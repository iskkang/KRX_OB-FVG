import requests
import pandas as pd
import datetime
from pykrx import stock

def get_kospi200_codes():
    """pykrx를 이용해 최신 코스피 200 종목 코드를 가져옵니다."""
    today = datetime.datetime.today().strftime("%Y%m%d")
    codes = stock.get_index_ticker_list(today, "1028")
    
    if not codes:
        target_date = stock.get_nearest_business_day_in_a_week(datetime.datetime.now().strftime("%Y%m%d"))
        codes = stock.get_index_ticker_list(target_date, "1028")
        
    return codes

def get_daily_ohlcv(base_url, token, stock_code):
    """
    키움 REST API를 통해 일봉 데이터를 조회합니다.
    (일봉 조회의 API ID 및 URL은 공식 문서의 일별 데이터 조회 엔드포인트에 맞게 조정 필요)
    """
    # 임시 URL (실제 키움 REST API의 '국내주식 일봉 데이터' 엔드포인트 입력)
    url = f"{base_url}/api/dostk/mrkcond" # <-- 제공된 문서에 따른 임시 URL. (실제 일봉 API URL로 교체 필요)
    
    # 키움 REST API 문서 기준 Header
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10004" # <-- 실제 일봉 차트 조회를 위한 api-id로 변경 필요 (ka10004는 호가요청)
    }
    
    body = {
        "stk_cd": f"KRX:{stock_code}"
    }
    
    try:
        # 키움 REST API는 Body에 값을 담아 POST 형식으로 요청할 수 있습니다.
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            return pd.DataFrame()

        data = response.json()
        
        # --- (주의) 응답 파싱 로직 ---
        # 실제 일봉 데이터가 담겨오는 JSON의 Key 값에 맞춰 아래 'items' 등을 수정하셔야 합니다.
        daily_data = data.get('items', []) 
        
        if not daily_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(daily_data)
        
        # 컬럼명 매핑 (API 응답값의 날짜, 시가, 고가, 저가, 종가 변수명으로 교체)
        # ex) df = df[['date', 'open', 'high', 'low', 'close']]
        # df.columns = ['date', 'open', 'high', 'low', 'close']
        
        df = df.sort_values('date').reset_index(drop=True)
        cols = ['open', 'high', 'low', 'close']
        df[cols] = df[cols].apply(pd.to_numeric)
        
        return df

    except Exception:
        return pd.DataFrame()
