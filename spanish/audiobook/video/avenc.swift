// ffmpeg 대신 쓰는 macOS 기본(AVFoundation) 인코더. render.py가 ffmpeg가 없을 때 컴파일해서 쓴다.
//
//   avenc <out.mp4> <width> <height> <fps> <audio.m4a> <audioStart> <audioDur> [bitrate]
//
// stdin으로 BGRA 원본 프레임(width*height*4바이트)을 받아 H.264로 쓰고,
// 끝나면 소리(audioStart부터 audioDur초)를 붙여 AAC 그대로(재인코딩 없이) mp4로 합친다.
import AVFoundation
import CoreMedia
import CoreVideo
import Foundation

func die(_ s: String) -> Never { FileHandle.standardError.write((s + "\n").data(using: .utf8)!); exit(1) }

let a = CommandLine.arguments
if a.count < 8 { die("usage: avenc out.mp4 w h fps audio.m4a start dur [bitrate]") }
let outURL = URL(fileURLWithPath: a[1])
let W = Int(a[2])!, H = Int(a[3])!, FPS = Int32(a[4])!
let audioURL = URL(fileURLWithPath: a[5])
let aStart = Double(a[6])!, aDur = Double(a[7])!
let bitrate = a.count > 8 ? Int(a[8])! : 8_000_000

let tmpURL = outURL.deletingPathExtension().appendingPathExtension("video.mp4")
try? FileManager.default.removeItem(at: tmpURL)
try? FileManager.default.removeItem(at: outURL)

// ---- 1단계: 화면만
let writer = try! AVAssetWriter(outputURL: tmpURL, fileType: .mp4)
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: W, AVVideoHeightKey: H,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: bitrate,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey: Int(FPS) * 2,
        AVVideoExpectedSourceFrameRateKey: Int(FPS),
    ],
])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H,
])
writer.add(input)
writer.startWriting()
writer.startSession(atSourceTime: .zero)

let frameBytes = W * H * 4
let fd = FileHandle.standardInput.fileDescriptor
let scratch = UnsafeMutableRawPointer.allocate(byteCount: frameBytes, alignment: 64)

// stdin에서 정확히 count바이트를 dst로 읽는다. EOF면 false.
func readFull(_ dst: UnsafeMutableRawPointer, _ count: Int) -> Bool {
    var got = 0
    while got < count {
        let r = read(fd, dst + got, count - got)
        if r <= 0 { return false }
        got += r
    }
    return true
}

var n: Int64 = 0
while true {
    while !input.isReadyForMoreMediaData { usleep(500) }
    var pb: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &pb)
    guard let px = pb else { die("pixel buffer") }
    CVPixelBufferLockBaseAddress(px, [])
    let dst = CVPixelBufferGetBaseAddress(px)!
    let bpr = CVPixelBufferGetBytesPerRow(px)
    var ok: Bool
    if bpr == W * 4 {
        ok = readFull(dst, frameBytes)                       // 바로 버퍼로
    } else {
        ok = readFull(scratch, frameBytes)
        if ok { for y in 0..<H { memcpy(dst + y * bpr, scratch + y * W * 4, W * 4) } }
    }
    CVPixelBufferUnlockBaseAddress(px, [])
    if !ok { break }
    if !adaptor.append(px, withPresentationTime: CMTime(value: n, timescale: FPS)) {
        die("append 실패: \(writer.error?.localizedDescription ?? "?")")
    }
    n += 1
}
input.markAsFinished()
let sem = DispatchSemaphore(value: 0)
writer.finishWriting { sem.signal() }
sem.wait()
if writer.status != .completed { die("화면 쓰기 실패: \(writer.error?.localizedDescription ?? "?")") }

// ---- 2단계: 소리 붙이기(재인코딩 없이)
let comp = AVMutableComposition()
let vAsset = AVURLAsset(url: tmpURL)
let aAsset = AVURLAsset(url: audioURL)
let vTrack = vAsset.tracks(withMediaType: .video)[0]
let aTrack = aAsset.tracks(withMediaType: .audio)[0]
let total = CMTime(value: n, timescale: FPS)
let cv = comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
try! cv.insertTimeRange(CMTimeRange(start: .zero, duration: vTrack.timeRange.duration), of: vTrack, at: .zero)
let ca = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
let aRange = CMTimeRange(start: CMTime(seconds: aStart, preferredTimescale: 48000),
                         duration: CMTimeMinimum(CMTime(seconds: aDur, preferredTimescale: 48000), total))
try! ca.insertTimeRange(aRange, of: aTrack, at: .zero)
guard let ex = AVAssetExportSession(asset: comp, presetName: AVAssetExportPresetPassthrough) else { die("export") }
ex.outputURL = outURL
ex.outputFileType = .mp4
ex.shouldOptimizeForNetworkUse = true
ex.exportAsynchronously { sem.signal() }
sem.wait()
if ex.status != .completed { die("합치기 실패: \(ex.error?.localizedDescription ?? "?")") }
try? FileManager.default.removeItem(at: tmpURL)
print("frames \(n)")
