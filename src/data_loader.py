import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from pykrx import stock

def get_kospi200_codes():
    """
    pykrx를 이용해 KOSPI 시가총액 상위 200개 종목 코드를 가져옵니다.
    당일 15:40 에는 KRX 당일 데이터 집계가 끝나지 않아 에러가 나므로,
    안전하게 '가장 최근에 확정된 과거 영업일' 데이터를 사용합니다.
    """
    # 1. GitHub Actions 환경을 고려하여 명시적으로 한국 시간(KST) 적용
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    
    # 2. 어제(now - 1일)를 기준으로 최근 10일간의 영업일 목록을 불러옴
    start_date = (now - timedelta(days=10)).strftime("%Y%m%d")
    end_date = (now - timedelta(days=1)).strftime("%Y%m%d")
    
    biz_days = stock.get_business_days_dates(start_date, end_date)
    
    if not biz_days:
        return []
        
    # 3. 무조건 데이터가 확정되어 있는 가장 마지막 영업일 선택
    target_date = biz_days[-1].strftime("%Y%m%d")
    
    try:
        # 안전한 날짜로 시가총액 조회
        df = stock.get_market_cap(target_date, market="KOSPI")
        
        if df.empty:
            return []
            
        # 시가총액 내림차순 정렬 후 상위 200개 추출
        codes = df.sort_values("시가총액", ascending=False).head(200).index.tolist()
        return codes
        
    except Exception as e:
        print(f"코스피 200 종목 조회 실패: {e}")
        return []

def get_daily_ohlcv(base_url, token, stock_code):
    """
    키움 REST API를 통해 일봉 데이터를 조회합니다.
    """
    # 임시 URL (실제 키움 REST API의 '국내주식 일봉 데이터' 엔드포인트)
    url = f"{base_url}/api/dostk/mrkcond" 
    
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10004" # 주의: 실제 일봉 조회 API ID로 변경 필요
    }
    
    body = {
        "stk_cd": f"KRX:{stock_code}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            return pd.DataFrame()

        data = response.json()
        
        daily_data = data.get('items', []) 
        
        if not daily_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(daily_data)
        
        # 과거 데이터가 위로 오도록 정렬
        df = df.sort_values('date').reset_index(drop=True)
        cols = ['open', 'high', 'low', 'close']
        df[cols] = df[cols].apply(pd.to_numeric)
        
        return df

    except Exception:
        return pd.DataFrame()
