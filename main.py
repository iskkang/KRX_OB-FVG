import os
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

from src.data_loader import get_kospi200_codes
from src.strategy import check_ob_fvg_signal
from src.telegram_bot import send_message

# --- Env
APP_KEY = os.getenv("KIWOOM_APP_KEY")
APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://mockapi.kiwoom.com"
KST = timezone(timedelta(hours=9))


def get_access_token() -> str | None:
    """
    키움 REST API 토큰 발급.
    - 응답 키는 access_token 이 아니라 'token' (키움 문서/실응답 기준)
    - 성공 판정은 return_code == 0 && token 존재
    """
    print("🔑 [인증] 접근 토큰(Access Token) 자동 발급을 시도합니다...", flush=True)

    url = f"{BASE_URL}/oauth2/token"
    headers = {"content-type": "application/json", "api-id": "au10001"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        try:
            data = resp.json()
        except Exception:
            print(f" ❌ 토큰 응답 JSON 파싱 실패. status={resp.status_code} body={resp.text[:500]}", flush=True)
            return None

        token = data.get("token")
        if data.get("return_code") == 0 and token:
            print(" ✅ 토큰 발급 성공!", flush=True)
            return token

        print(f" ❌ 토큰 발급 실패: status={resp.status_code} payload={data}", flush=True)
        return None

    except Exception as e:
        print(f" ❌ 토큰 요청 중 에러 발생: {e}", flush=True)
        return None


def fetch_daily_ohlcv_with_retry(
    base_url: str,
    token: str,
    stock_code: str,
    max_retries_429: int = 5,
    timeout_sec: int = 15,
) -> tuple[pd.DataFrame, str]:
    """
    ka10081 일봉 조회 (429 레이트리밋 재시도 포함)
    Returns:
      (df, status)
        status:
          - "ok"
          - "rate_limited"
          - "api_error"
          - "no_data"
          - "exception"
    """
    url = f"{base_url}/api/dostk/chart"
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10081",
    }
    today_str = datetime.now(KST).strftime("%Y%m%d")

    body = {
        "stk_cd": f"KRX:{stock_code}",
        "base_dt": today_str,
        "upd_stkpc_tp": "1",
    }

    backoff = 1.0
    for attempt in range(1, max_retries_429 + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout_sec)

            # --- 429: rate limit
            if resp.status_code == 429:
                # 키움이 주는 상세 메시지 출력
                detail = resp.text[:300]
                print(
                    f" 👉 [429 RATE LIMIT] {stock_code} (attempt {attempt}/{max_retries_429}) "
                    f"=> sleep {backoff:.1f}s | {detail}",
                    flush=True,
                )
                time.sleep(backoff + random.uniform(0, 0.25))  # tiny jitter
                backoff = min(backoff * 2, 20.0)
                continue

            # --- Non-200
            if resp.status_code != 200:
                print(f" 👉 [API 에러] {stock_code} status={resp.status_code}, 상세: {resp.text[:500]}", flush=True)
                return pd.DataFrame(), "api_error"

            # --- Parse
            data = resp.json()
            daily = data.get("stk_dt_pole_chart_qry", [])
            if not daily:
                # 정상인데 데이터 없음일 수 있어서 구분
                print(f" 👉 [데이터 없음] {stock_code} 응답: {str(data)[:500]}", flush=True)
                return pd.DataFrame(), "no_data"

            df = pd.DataFrame(daily)
            df = df[["dt", "open_pric", "high_pric", "low_pric", "cur_prc"]]
            df.columns = ["date", "open", "high", "low", "close"]
            df = df.sort_values("date").reset_index(drop=True)
            df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].apply(
                pd.to_numeric, errors="coerce"
            )
            return df, "ok"

        except Exception as e:
            print(f" 👉 [예외] {stock_code} 요청 중 오류: {e}", flush=True)
            # 예외도 짧게 백오프
            time.sleep(min(backoff, 5.0))
            backoff = min(backoff * 2, 20.0)

    # retries exhausted
    return pd.DataFrame(), "rate_limited"


def main():
    print("🚀 [GitHub Actions] KRX OB+FVG 스캐너 시작", flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, "🚀 **[GitHub Actions] 코스피200 OB+FVG 스캔 시작**")

    # --- env check
    if not APP_KEY or not APP_SECRET:
        print("❌ 환경변수에 KIWOOM_APP_KEY 또는 KIWOOM_APP_SECRET이 없습니다.", flush=True)
        send_message(TG_TOKEN, TG_CHAT_ID, "❌ 환경변수 누락: KIWOOM_APP_KEY / KIWOOM_APP_SECRET")
        return

    # --- token
    access_token = get_access_token()
    if not access_token:
        print("❌ 토큰이 없어 차트 조회를 진행할 수 없습니다. 프로그램을 종료합니다.", flush=True)
        send_message(TG_TOKEN, TG_CHAT_ID, "❌ 토큰 발급 실패로 스캔 중단")
        return

    # --- universe
    codes = get_kospi200_codes(BASE_URL, access_token)
    total = len(codes)
    print(f"✅ 대상 종목 수: {total}개", flush=True)

    if total == 0:
        print("❌ 스캔할 종목이 없습니다. 프로그램을 종료합니다.", flush=True)
        send_message(TG_TOKEN, TG_CHAT_ID, "❌ 스캔할 종목 0개")
        return

    # --- results
    found = []
    failed = []  # list[(code, reason)]
    no_signal_cnt = 0

    # --- throttle baseline (429가 자주 뜨면 0.8~1.2로 올려라)
    base_sleep = 0.35

    # --- scan loop
    for i, code in enumerate(codes, 1):
        print(f"[{i}/{total}] 🔍 종목코드 ({code}) 차트 조회 중...", end="", flush=True)

        # 기본 속도 제한(서버 리밋 완화)
        time.sleep(base_sleep)

        df, status = fetch_daily_ohlcv_with_retry(BASE_URL, access_token, code)

        if df.empty:
            # status별로 깔끔하게 누적
            if status == "rate_limited":
                print(" ⚠️ 데이터 없음 (429 재시도 후 실패)", flush=True)
                failed.append((code, "429_rate_limit"))
            elif status == "api_error":
                print(" ⚠️ 데이터 없음 (API 오류)", flush=True)
                failed.append((code, "api_error"))
            elif status == "no_data":
                print(" ⚠️ 데이터 없음 (응답 no_data)", flush=True)
                failed.append((code, "no_data"))
            else:
                print(" ⚠️ 데이터 없음 (exception)", flush=True)
                failed.append((code, "exception"))
            continue

        is_signal, prices = check_ob_fvg_signal(df)

        if is_signal:
            entry, sl, tp = prices
            msg = (
                f"🎯 **[OB+FVG] 타점 포착**\n"
                f"진행: {i}/{total}\n"
                f"종목코드: `{code}`\n"
                f"진입: {entry:,.0f}원\n"
                f"손절: {sl:,.0f}원\n"
                f"익절: {tp:,.0f}원\n"
                f"[네이버증권](https://finance.naver.com/item/main.naver?code={code})"
            )
            print(" 👉 🎯 타점 포착!", flush=True)
            send_message(TG_TOKEN, TG_CHAT_ID, msg)
            found.append(code)
        else:
            no_signal_cnt += 1
            print(" ➖ 시그널 없음", flush=True)

        # (선택) 진행률 텔레그램 중간 리포트: 너무 스팸이면 주석 처리
        # if i % 50 == 0:
        #     send_message(TG_TOKEN, TG_CHAT_ID, f"⏳ 진행률: {i}/{total} | 발견 {len(found)} | 실패 {len(failed)}")

    # --- final summary
    summary = (
        f"🏁 **스캔 완료**\n"
        f"총 대상: {total}\n"
        f"발견: {len(found)}\n"
        f"무시(시그널 없음): {no_signal_cnt}\n"
        f"실패(데이터 미수신): {len(failed)}"
    )
    print("\n" + summary, flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, summary)

    # --- failed only summary (마지막에만)
    if failed:
        # reason별 집계
        counts = {}
        for _, r in failed:
            counts[r] = counts.get(r, 0) + 1

        # 목록은 너무 길면 잘라서 전송(텔레그램 길이/가독성)
        codes_only = [c for c, _ in failed]
        preview = ", ".join(codes_only[:40]) + (" ..." if len(codes_only) > 40 else "")

        fail_msg = (
            "⚠️ **실패 종목 요약(데이터 미수신)**\n"
            + "\n".join([f"- {k}: {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])])
            + "\n\n"
            + f"목록(최대 40개):\n`{preview}`"
        )
        send_message(TG_TOKEN, TG_CHAT_ID, fail_msg)


if __name__ == "__main__":
    main()
