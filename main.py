import os
import time
from src.data_loader import get_kospi200_codes, get_daily_ohlcv
from src.strategy import check_ob_fvg_signal
from src.telegram_bot import send_message

# GitHub Secrets에서 환경변수 로드
ACCESS_TOKEN = os.getenv("KIWOOM_ACCESS_TOKEN")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://mockapi.kiwoom.com"

def main():
    print("🚀 [GitHub Actions] KRX OB+FVG 스캐너 시작", flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, "🚀 **[GitHub Actions] 코스피200 OB+FVG 스캔 시작**")

    # 1. 대상 종목 리스트 확보
    codes = get_kospi200_codes()
    total_count = len(codes)
    print(f"✅ 대상 종목 수: {total_count}개", flush=True)
    
    if total_count == 0:
        print("❌ 스캔할 종목이 없습니다. 프로그램을 종료합니다.", flush=True)
        return

    found_stocks = []

    # 2. 스캔 시작
    for i, code in enumerate(codes, 1):
        print(f"[{i}/{total_count}] 🔍 종목코드 ({code}) 차트 조회 중...", end="", flush=True)

        # API 제한 고려 (0.3초 대기)
        time.sleep(0.3)
        
        # 차트 데이터 조회
        df = get_daily_ohlcv(BASE_URL, ACCESS_TOKEN, code)
        
        if df.empty:
            print(f" ⚠️ 데이터 없음 (API 오류 또는 스킵)", flush=True)
            continue
            
        # 전략 판별
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
            print(f" 👉 🎯 타점 포착!", flush=True)
            send_message(TG_TOKEN, TG_CHAT_ID, msg)
            found_stocks.append(code)
        else:
            print(f" ➖ 시그널 없음", flush=True)

    # 3. 종료
    end_msg = f"🏁 **스캔 완료**\n총 {len(found_stocks)} 종목 발견"
    print("\n" + end_msg, flush=True)
    send_message(TG_TOKEN, TG_CHAT_ID, end_msg)

if __name__ == "__main__":
    main()
