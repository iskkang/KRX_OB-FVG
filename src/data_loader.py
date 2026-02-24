import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from pykrx import stock

def get_kospi200_codes():
    """
    pykrx를 이용해 KOSPI 시가총액 상위 200개 종목 코드를 가져옵니다.
    안전하게 '가장 최근에 확정된 과거 영업일' 데이터를 사용합니다.
    """
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    
    start_date = (now - timedelta(days=10)).strftime("%Y%m%d")
    end_date = (now - timedelta(days=1)).strftime("%Y%m%d")
    
    # 수정완료: get_business_days_dates -> get_business_days
    biz_days = stock.get_business_days(start_date, end_date)
    
    # DatetimeIndex가 비어있는지 확인
    if len(biz_days) == 0:
        return []
        
    target_date = biz_days[-1].strftime("%Y%m%d")
    
    try:
        df = stock.get_market_cap(target_date, market="KOSPI")
        
        if df.empty:
            return []
            
        codes = df.sort_values("시가총액", ascending=False).head(200).index.tolist()
        return codes
        
    except Exception as e:
        print(f"코스피 200 종목 조회 실패: {e}")
        return []

def get_daily_ohlcv(base_url, token, stock_code):
    """
    키움 REST API를 통해 일봉 데이터를 조회합니다.
    """
    url = f"{base_url}/api/dostk/mrkcond" 
    
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10004" # 주의: 올려주신 문서의 ka10004는 '주식호가요청' 입니다. 일봉 데이터를 받으려면 일봉 API ID로 변경해야 합니다.
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
        
        df = df.sort_values('date').reset_index(drop=True)
        cols = ['open', 'high', 'low', 'close']
        df[cols] = df[cols].apply(pd.to_numeric)
        
        return df

    except Exception:
        return pd.DataFrame()
