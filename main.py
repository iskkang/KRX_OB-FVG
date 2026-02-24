# main.py

import os
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

from src.data_loader import (
    get_kospi200_codes,
    get_daily_ohlcv,
)
from src.strategy import check_ob_fvg_signal
from src.telegram_bot import send_message


# =====================
# Environment
# =====================
APP_KEY = os.getenv("KIWOOM_APP_KEY")
APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://mockapi.kiwoom.com"
KST = timezone(timedelta(hours=9))


# =====================
# Token
# =====================
def get_access_token() -> str | None:
    print("🔑 [인증] 접근 토큰(Access Token) 자동 발급을 시도합니다...", flush=True)

    url = f"{BASE_URL}/oauth2/token"
    headers = {
        "content-type": "application/json",
        "api-id": "au10001",
    }
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        data = resp.json()

        token = data.get("token")
        if data.get("return_code") == 0 and token:
            print(" ✅ 토큰 발급 성공!", flush=True)
            return token

        print(f" ❌ 토큰 발급 실패: {data}", flush=True)
        return None

    except Exception as e:
        print(f" ❌ 토큰 요청 중 에러: {e}", flush=True)
        return None


# =====================
# Main
# =====================
def main():
    print("🚀 [GitHub Actions] KRX OB+FVG 스캐너 시작", flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, "🚀 **[KRX OB+FVG] 스캔 시작**")

    # --- env check
    if not APP_KEY or not APP_SECRET:
        msg = "❌ 환경변수 누락: KIWOOM_APP_KEY / KIWOOM_APP_SECRET"
        print(msg, flush=True)
        send_message(TG_TOKEN, TG_CHAT_ID, msg)
        return

    # --- token
    access_token = get_access_token()
    if not access_token:
        msg = "❌ 토큰 발급 실패로 스캔 중단"
        print(msg, flush=True)
        send_message(TG_TOKEN, TG_CHAT_ID, msg)
        return

    # --- universe (KOSPI200)
    try:
        codes = get_kospi200_codes(BASE_URL, access_token)
    except Exception as e:
        msg = f"❌ KOSPI200 조회 실패\n{e}"
        print(msg, flush=True)
        send_message(TG_TOKEN, TG_CHAT_ID, msg)
        return

    total = len(codes)
    print(f"✅ 대상 종목 수: {total}개", flush=True)

    if total == 0:
        msg = "❌ KOSPI200 종목 0개"
        print(msg, flush=True)
        send_message(TG_TOKEN, TG_CHAT_ID, msg)
        return

    found = []
    failed = []
    no_signal_cnt = 0

    base_sleep = 0.35  # 기본 호출 간격

    # =====================
    # Scan Loop
    # =====================
    for i, code in enumerate(codes, 1):
        print(f"[{i}/{total}] 🔍 {code} 차트 조회...", end="", flush=True)
        time.sleep(base_sleep)

        df = get_daily_ohlcv(BASE_URL, access_token, code)

        if df.empty:
            print(" ⚠️ 데이터 없음", flush=True)
            failed.append(code)
            continue

        is_signal, prices = check_ob_fvg_signal(df)

        if is_signal:
            entry, sl, tp = prices
            msg = (
                f"🎯 **[OB+FVG 시그널]**\n"
                f"진행: {i}/{total}\n"
                f"종목: `{code}`\n"
                f"진입: {entry:,.0f}\n"
                f"손절: {sl:,.0f}\n"
                f"익절: {tp:,.0f}\n"
                f"[네이버증권](https://finance.naver.com/item/main.naver?code={code})"
            )
            print(" 👉 🎯 시그널!", flush=True)
            send_message(TG_TOKEN, TG_CHAT_ID, msg)
            found.append(code)
        else:
            no_signal_cnt += 1
            print(" ➖ 없음", flush=True)

    # =====================
    # Summary
    # =====================
    summary = (
        f"🏁 **스캔 완료**\n"
        f"총 종목: {total}\n"
        f"시그널: {len(found)}\n"
        f"무시: {no_signal_cnt}\n"
        f"실패: {len(failed)}"
    )
    print(summary, flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, summary)

    if failed:
        preview = ", ".join(failed[:40]) + (" ..." if len(failed) > 40 else "")
        fail_msg = (
            "⚠️ **데이터 수신 실패 종목**\n"
            f"`{preview}`"
        )
        send_message(TG_TOKEN, TG_CHAT_ID, fail_msg)


if __name__ == "__main__":
    main()
