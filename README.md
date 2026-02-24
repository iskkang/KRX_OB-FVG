# krx_OB+FVG Scanner 🚀

코스피 200 종목을 대상으로 Order Block(OB) + Fair Value Gap(FVG) 패턴을 자동으로 검색하여 텔레그램으로 알림을 보내주는 봇입니다.

## 특징
- **GitHub Actions 기반**: 별도의 서버 없이 100% 클라우드 자동 실행
- **자동 토큰 갱신**: 매 실행 시 키움 API 토큰을 새로 받아 만료 걱정 없음
- **KOSPI 200 타겟**: 유동성이 풍부한 우량주 위주 스캔

## 설치 및 사용법
1. 이 저장소를 Fork 또는 Clone 합니다.
2. GitHub Repository의 **Settings > Secrets and variables > Actions** 메뉴로 이동합니다.
3. 아래의 Repository Secret을 등록합니다.
   - `KIWOOM_APP_KEY`: 키움증권 발급 App Key
   - `KIWOOM_APP_SECRET`: 키움증권 발급 Secret Key
   - `KIWOOM_ACCOUNT`: 모의투자 계좌번호 (선택사항)
   - `TELEGRAM_TOKEN`: 텔레그램 봇 토큰
   - `TELEGRAM_CHAT_ID`: 텔레그램 Chat ID

## 실행 스케줄
- 매주 월~금 한국시간 오후 3시 40분 (장 마감 직후) 자동 실행됩니다.
