#!/usr/bin/env python3
"""청주 출발 항공권 시세 텔레그램 봇.

시세·여행창 데이터는 trip.html 안의 <script type="application/json" id="fare-data">
블록 한 곳에서만 읽는다. 웹페이지와 봇이 같은 블록을 쓰므로 값이 어긋날 일이 없다.

사용법:
    python3 bot/fare_bot.py digest              # 정기 요약 발송
    python3 bot/fare_bot.py poll                # 받은 질문에 답장
    python3 bot/fare_bot.py digest --dry-run    # 보내지 않고 출력만

환경변수:
    TELEGRAM_BOT_TOKEN   @BotFather에서 받은 토큰
    TELEGRAM_CHAT_ID     digest를 보낼 대화 ID
    BOT_STATE            poll 오프셋 저장 경로 (기본 bot/state.json)
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "trip.html"
KST = timezone(timedelta(hours=9))
API = "https://api.telegram.org/bot{token}/{method}"

DEST_WORDS = {
    "oka": ["오키나와", "나하", "oka", "okinawa", "일본"],
    "twn": ["대만", "타이베이", "타이완", "tpe", "taipei", "taiwan"],
}


# ---------------------------------------------------------------- 데이터

def load_fare(page: Path = PAGE) -> dict:
    """trip.html에서 fare-data JSON 블록만 뽑아 읽는다."""
    text = page.read_text(encoding="utf-8")
    m = re.search(
        r'<script[^>]*id="fare-data"[^>]*>(.*?)</script>', text, re.S
    )
    if not m:
        raise SystemExit(f"{page} 안에서 fare-data 블록을 찾지 못했습니다.")
    return json.loads(m.group(1))


def won(n) -> str:
    return f"{round(n):,}원"


# ---------------------------------------------------------------- 계산
# 아래 세 함수는 trip.html의 scoreFor / gradeFor / rankWindows와 같은 식이다.

def score_for(price: float, band: dict) -> float:
    t = (price - band["low"]) / (band["high"] - band["low"])
    t = min(1.0, max(0.0, t))
    return round((5 - 4 * t) * 10) / 10


def grade_for(score: float) -> int:
    for cut, g in ((4.5, 5), (3.5, 4), (2.5, 3), (1.5, 2)):
        if score >= cut:
            return g
    return 1


def window_price(fare: dict, win: dict, dest: str) -> int:
    band = fare["destinations"][dest]["months"][win["month"]]
    sc = fare["scoring"]
    raw = (band["avg"] * sc["holidayMultiplier"] if win["holiday"]
           else band["low"] * sc["weekendMultiplier"])
    return round(raw / 1000) * 1000


def rank_windows(fare: dict, dest: str) -> list:
    sc = fare["scoring"]
    rows = [{"w": w,
             "price": window_price(fare, w, dest),
             "eff": w["days"] / (w["leave"] + 1)}
            for w in fare["windows"]]

    prices = [r["price"] for r in rows]
    effs = [r["eff"] for r in rows]
    p_min, p_max = min(prices), max(prices)
    e_min, e_max = min(effs), max(effs)

    for r in rows:
        pv = sc["price"] if p_max == p_min else \
            sc["price"] * (p_max - r["price"]) / (p_max - p_min)
        ev = sc["leave"] if e_max == e_min else \
            sc["leave"] * (r["eff"] - e_min) / (e_max - e_min)
        r["score"] = round(pv + ev + fare["season"][dest][r["w"]["month"]])

    rows.sort(key=lambda r: (-r["score"], r["price"]))
    return rows


def cheapest_month(fare: dict, dest: str) -> str:
    months = fare["destinations"][dest]["months"]
    return min(months, key=lambda m: months[m]["low"])


# ---------------------------------------------------------------- 메시지

def route_line(fare: dict, dest: str) -> str:
    o, d = fare["origin"], fare["destinations"][dest]
    return (f"<b>{html.escape(o['city'])} {o['iata']} → "
            f"{html.escape(d['city'])} {d['iata']}</b>")


def compose_digest(fare: dict, today: datetime | None = None) -> str:
    today = today or datetime.now(KST)
    out = [f"✈️ <b>청주 출발 항공권 시세</b>  ({today.month}월 {today.day}일)", ""]

    for dest in fare["destinations"]:
        d = fare["destinations"][dest]
        best = cheapest_month(fare, dest)
        out.append(route_line(fare, dest))
        for mo, band in d["months"].items():
            mark = "  ← 최저" if mo == best else ""
            out.append(f"<code>{mo}월</code>  {won(band['low'])}"
                       f"  <i>평균 {band['avg']:,}</i>"
                       f"  {html.escape(band['tag'])}{mark}")
        out.append("")

    out.append("<b>주말 낀 추천 기간</b>")
    for dest in fare["destinations"]:
        d = fare["destinations"][dest]
        out.append(f"― {html.escape(d['name'])} ({fare['origin']['iata']}→{d['iata']})")
        for i, r in enumerate(rank_windows(fare, dest)[:3], 1):
            w = r["w"]
            leave = "연차 0일" if w["leave"] == 0 else f"연차 {w['leave']}일"
            out.append(
                f"{i}. {w['from']}({w['fdow']})→{w['to']}({w['tdow']})"
                f"  {w['nights']}박{w['days']}일 · {leave}"
                f"  <b>{won(r['price'])}</b>"
            )
        out.append("")

    out.append(f'<a href="{fare["page"]}">시세판 열기</a>')
    out.append(f"<i>{html.escape(fare['basis'])}</i>")
    return "\n".join(out)


def compose_verdict(fare: dict, dest: str, month: str, price: int) -> str:
    d = fare["destinations"][dest]
    band = d["months"][month]
    score = score_for(price, band)
    grade = grade_for(score)
    label = fare["grades"][str(grade)]["label"]

    bar = "█" * grade + "░" * (5 - grade)
    diff = price - band["avg"]
    if diff == 0:
        rel = "이 달 평균과 같습니다."
    elif diff < 0:
        rel = f"이 달 평균보다 {won(-diff)} 쌉니다."
    else:
        rel = f"이 달 평균보다 {won(diff)} 비쌉니다."

    return "\n".join([
        route_line(fare, dest) + f"  ·  {month}월  ·  왕복 1인",
        "",
        f"넣은 값  <b>{won(price)}</b>",
        f"{bar}  <b>{score:.1f}/5 · {html.escape(label)}</b>",
        rel,
        "",
        f"<code>최저 {band['low']:,} · 평균 {band['avg']:,} · 고가 {band['high']:,}</code>",
        "",
        html.escape(d["msgs"][str(grade)]),
        html.escape(band["note"]),
        "",
        f'<a href="{fare["page"]}">시세판에서 보기</a>',
    ])


HELP = (
    "청주 출발 오키나와·대만 왕복 시세를 봅니다.\n\n"
    "<b>값이 괜찮은지 물어보기</b>\n"
    "<code>오키나와 11월 245000</code> 처럼 보내면 추천도로 답합니다.\n"
    "목적지를 빼면 오키나와, 달을 빼면 11월로 봅니다.\n\n"
    "<b>명령</b>\n"
    "<code>/시세</code> 여섯 조합 요약과 추천 기간\n"
    "<code>/도움</code> 이 안내"
)


# ---------------------------------------------------------------- 질문 해석

def parse_question(fare: dict, text: str) -> tuple | None:
    """'오키나와 11월 245000' 같은 문장에서 (dest, month, price)를 뽑는다."""
    low = text.lower()

    dest = None
    for key, words in DEST_WORDS.items():
        if any(w in low for w in words):
            dest = key
            break

    month = None
    mm = re.search(r"\b(1[0-2])\s*월", text)
    if mm:
        month = mm.group(1)

    # 달 표기를 지운 뒤 남는 큰 숫자를 값으로 본다.
    stripped = re.sub(r"\b1[0-2]\s*월", " ", text)
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]{3,}", stripped)]
    nums = [n for n in nums if 10_000 <= n <= 5_000_000]
    if not nums:
        return None

    price = nums[0]
    dest = dest or "oka"
    if month not in fare["destinations"][dest]["months"]:
        month = "11"
    return dest, month, price


# ---------------------------------------------------------------- 텔레그램

def api_call(token: str, method: str, **params) -> dict:
    url = API.format(token=token, method=method)
    body = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None}
    ).encode()
    try:
        with urllib.request.urlopen(url, data=body, timeout=40) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise SystemExit(f"텔레그램 API {method} 실패 ({e.code}): {detail}")


def send(token: str, chat_id: str, text: str) -> None:
    api_call(token, "sendMessage", chat_id=chat_id, text=text,
             parse_mode="HTML", disable_web_page_preview="true")


def read_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


# ---------------------------------------------------------------- 실행

def cmd_digest(fare: dict, args) -> int:
    text = compose_digest(fare)
    if args.dry_run:
        print(text)
        return 0
    send(need("TELEGRAM_BOT_TOKEN"), need("TELEGRAM_CHAT_ID"), text)
    print("digest 발송 완료")
    return 0


def cmd_poll(fare: dict, args) -> int:
    token = need("TELEGRAM_BOT_TOKEN")
    state_path = Path(os.environ.get("BOT_STATE", ROOT / "bot" / "state.json"))
    state = read_state(state_path)
    offset = state.get("offset")

    resp = api_call(token, "getUpdates",
                    offset=offset, timeout=0, allowed_updates='["message"]')
    updates = resp.get("result", [])
    if not updates:
        print("새 메시지 없음")
        return 0

    # 저장된 오프셋이 없으면 (캐시 유실 등) 묵은 메시지에 뒤늦게 답하지 않는다.
    first_run = offset is None
    answered = 0

    for up in updates:
        state["offset"] = up["update_id"] + 1
        msg = up.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat = str((msg.get("chat") or {}).get("id", ""))
        if not text or not chat or first_run:
            continue

        if text.startswith(("/start", "/help", "/도움")):
            reply = HELP
        elif text.startswith(("/시세", "/digest", "/fare")):
            reply = compose_digest(fare)
        else:
            parsed = parse_question(fare, text)
            if not parsed:
                continue
            reply = compose_verdict(fare, *parsed)

        if args.dry_run:
            print(f"[{chat}] {text}\n{reply}\n{'-' * 40}")
        else:
            send(token, chat, reply)
        answered += 1

    write_state(state_path, state)
    print(f"{len(updates)}건 확인, {answered}건 답장"
          + (" (첫 실행이라 묵은 메시지는 건너뜀)" if first_run else ""))
    return 0


def cmd_ask(fare: dict, args) -> int:
    parsed = parse_question(fare, " ".join(args.words))
    if not parsed:
        print("값을 못 알아들었습니다. 예: 오키나와 11월 245000")
        return 1
    print(compose_verdict(fare, *parsed))
    return 0


def need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"환경변수 {name}이(가) 없습니다.")
    return value


def main() -> int:
    ap = argparse.ArgumentParser(description="청주 출발 항공권 시세 봇")
    ap.add_argument("mode", choices=["digest", "poll", "ask"])
    ap.add_argument("words", nargs="*", help="ask 모드에서 물어볼 문장")
    ap.add_argument("--dry-run", action="store_true",
                    help="보내지 않고 화면에 출력만")
    args = ap.parse_args()

    fare = load_fare()
    return {"digest": cmd_digest, "poll": cmd_poll, "ask": cmd_ask}[args.mode](fare, args)


if __name__ == "__main__":
    sys.exit(main())
