import os
import time
import requests

from src.data_loader import get_kospi200_codes, get_daily_ohlcv
from src.strategy import check_ob_fvg_signal
from src.telegram_bot import send_message

# GitHub Secrets에서 APP_KEY와 APP_SECRET 로드
APP_KEY = os.getenv("KIWOOM_APP_KEY")
APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://mockapi.kiwoom.com"


def get_access_token() -> str | None:
    """
    APP_KEY / APP_SECRET(=secretkey)로 키움 REST API 접근 토큰을 발급받습니다.
    ※ 응답 JSON 키는 access_token 이 아니라 'token' 입니다. (문서/응답 기준)
    """
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
        response = requests.post(url, headers=headers, json=body, timeout=15)

        # JSON 파싱(실패 시 원문 출력)
        try:
            data = response.json()
        except Exception:
            print(f" ❌ 토큰 응답 JSON 파싱 실패. status={response.status_code} body={response.text[:500]}", flush=True)
            return None

        # ✅ 성공 판정: return_code == 0 이고 token 존재
        token = data.get("token")
        return_code = data.get("return_code")

        if return_code == 0 and token:
            print(" ✅ 토큰 발급 성공!", flush=True)
            return token

        # 실패/예외 케이스 로깅 강화
        print(f" ❌ 토큰 발급 실패: status={response.status_code} payload={data}", flush=True)
        return None

    except requests.RequestException as e:
        print(f" ❌ 토큰 요청 중 네트워크 에러 발생: {e}", flush=True)
        return None
    except Exception as e:
        print(f" ❌ 토큰 요청 중 에러 발생: {e}", flush=True)
        return None


def main():
    print("🚀 [GitHub Actions] KRX OB+FVG 스캐너 시작", flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, "🚀 **[GitHub Actions] 코스피200 OB+FVG 스캔 시작**")

    # 1) 환경변수 체크
    if not APP_KEY or not APP_SECRET:
        print("❌ 환경변수에 KIWOOM_APP_KEY 또는 KIWOOM_APP_SECRET이 없습니다.", flush=True)
        return

    # 2) 토큰 발급
    access_token = get_access_token()
    if not access_token:
        print("❌ 토큰이 없어 차트 조회를 진행할 수 없습니다. 프로그램을 종료합니다.", flush=True)
        return

    # 3) 대상 종목 리스트 확보
    codes = get_kospi200_codes()
    total_count = len(codes)
    print(f"✅ 대상 종목 수: {total_count}개", flush=True)

    if total_count == 0:
        print("❌ 스캔할 종목이 없습니다. 프로그램을 종료합니다.", flush=True)
        return

    found_stocks = []

    # 4) 스캔 시작
    for i, code in enumerate(codes, 1):
        print(f"[{i}/{total_count}] 🔍 종목코드 ({code}) 차트 조회 중...", end="", flush=True)

        time.sleep(1.3)

        df = get_daily_ohlcv(BASE_URL, access_token, code)

        if df.empty:
            print(" ⚠️ 데이터 없음 (API 오류 또는 스킵)", flush=True)
            continue

        is_signal, prices = check_ob_fvg_signal(df)

        if is_signal:
            entry, sl, tp = prices
            msg = (
                f"🎯 **[OB+FVG] 타점 포착**\n"
                f"종목코드: `{code}`\n"
                f"진입: {entry:,.0f}원\n"
                f"손절: {sl:,.0f}원\n"
                f"익절: {tp:,.0f}원\n"
                f"[네이버증권](https://finance.naver.com/item/main.naver?code={code})"
            )
            print(" 👉 🎯 타점 포착!", flush=True)
            send_message(TG_TOKEN, TG_CHAT_ID, msg)
            found_stocks.append(code)
        else:
            print(" ➖ 시그널 없음", flush=True)

    # 5) 종료
    end_msg = f"🏁 **스캔 완료**\n총 {len(found_stocks)} 종목 발견"
    print("\n" + end_msg, flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, end_msg)


if __name__ == "__main__":
    main()
