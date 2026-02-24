import requests
import pandas as pd
import datetime
from pykrx import stock

def get_kospi200_codes():
    """
    pykrx를 이용해 KOSPI 시가총액 상위 200개 종목 코드를 가져옵니다.
    (인덱스 코드 오류를 방지하기 위해 시가총액 정렬 방식을 사용합니다.)
    """
    today = datetime.datetime.today().strftime("%Y%m%d")
    
    # 1. 코스피 전 종목 시가총액 데이터 조회 (DataFrame 반환)
    df = stock.get_market_cap(today, market="KOSPI")
    
    # 2. 주말이나 휴일이라 오늘 데이터가 비어있다면 최근 영업일로 재조회
    if df.empty:
        target_date = stock.get_nearest_business_day_in_a_week(datetime.datetime.now().strftime("%Y%m%d"))
        df = stock.get_market_cap(target_date, market="KOSPI")
        
    # 3. 시가총액(Market Cap) 내림차순 정렬 후 상위 200개의 종목코드만 리스트로 추출
    codes = df.sort_values("시가총액", ascending=False).head(200).index.tolist()
        
    return codes

def get_daily_ohlcv(base_url, token, stock_code):
    """
    키움 REST API를 통해 일봉 데이터를 조회합니다.
    """
    # 임시 URL (실제 키움 REST API의 '국내주식 일봉 데이터' 엔드포인트 입력)
    url = f"{base_url}/api/dostk/mrkcond" 
    
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10004" 
    }
    
    body = {
        "stk_cd": f"KRX:{stock_code}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            return pd.DataFrame()

        data = response.json()
        
        # --- (주의) 응답 파싱 로직 ---
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
