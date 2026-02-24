import os
import time
from src.auth import get_access_token
from src.data_loader import get_kospi200_codes, get_daily_ohlcv
from src.strategy import check_ob_fvg_signal
from src.telegram_bot import send_message

# GitHub Secrets에서 환경변수 로드
APP_KEY = os.getenv("KIWOOM_APP_KEY")
APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
ACCOUNT = os.getenv("KIWOOM_ACCOUNT")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 모의투자 URL
BASE_URL = "https://openapivts.kiwoom.com:29443"

def main():
    print("🚀 [GitHub Actions] KRX OB+FVG 스캐너 시작")
    send_message(TG_TOKEN, TG_CHAT_ID, "🚀 **[GitHub Actions] 코스피200 OB+FVG 스캔 시작**")

    # 1. 토큰 발급 (자동 로그인)
    token = get_access_token(BASE_URL, APP_KEY, APP_SECRET)
    if not token:
        send_message(TG_TOKEN, TG_CHAT_ID, "❌ API 토큰 발급 실패. 스캔을 중단합니다.")
        return

    # 2. 종목 리스트 확보
    codes = get_kospi200_codes()
    print(f"대상 종목 수: {len(codes)}개")
    
    found_stocks = []

    # 3. 스캔 시작
    for i, code in enumerate(codes):
        # API 제한 고려 (0.2초 대기)
        time.sleep(0.2)
        
        # 데이터 조회
        df = get_daily_ohlcv(BASE_URL, token, APP_KEY, APP_SECRET, ACCOUNT, code)
        
        # 전략 판별
        is_signal, prices = check_ob_fvg_signal(df)
        
        if is_signal:
            entry, sl, tp = prices
            msg = (
                f"🎯 **[OB+FVG] 타점 포착**\n"
                f"Code: `{code}`\n"
                f"진입: {entry:,.0f}원\n"
                f"손절: {sl:,.0f}원\n"
                f"익절: {tp:,.0f}원\n"
                f"[네이버증권](https://finance.naver.com/item/main.naver?code={code})"
            )
            print(f"Found: {code}")
            send_message(TG_TOKEN, TG_CHAT_ID, msg)
            found_stocks.append(code)

    # 4. 종료
    end_msg = f"🏁 **스캔 완료**\n총 {len(found_stocks)} 종목 발견"
    print(end_msg)
    send_message(TG_TOKEN, TG_CHAT_ID, end_msg)

if __name__ == "__main__":
    main()
