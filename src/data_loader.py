import requests
import pandas as pd
import datetime
from pykrx import stock

def get_kospi200_codes():
    """pykrx를 이용해 최신 코스피 200 종목 코드를 가져옵니다."""
    today = datetime.datetime.today().strftime("%Y%m%d")
    codes = stock.get_index_ticker_list(today, "1028") # 1028: KOSPI 200
    
    # 휴일이라 데이터가 없으면 최근 영업일 기준으로 재시도
    if not codes:
        target_date = stock.get_nearest_business_day_in_a_week(datetime.datetime.now().strftime("%Y%m%d"))
        codes = stock.get_index_ticker_list(target_date, "1028")
        
    return codes

def get_daily_ohlcv(base_url, token, app_key, app_secret, account_num, stock_code):
    """키움 REST API로 일봉 데이터 조회"""
    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST01010400" # 키움 모의투자/실전 API 문서 확인 필요
    }
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            return pd.DataFrame()

        data = response.json()
        daily_data = data.get('output2', [])
        
        if not daily_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(daily_data)
        
        # 컬럼명 매핑 (API 응답값에 따라 수정 필요할 수 있음)
        df = df[['stck_bsop_date', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'stck_clpr']]
        df.columns = ['date', 'open', 'high', 'low', 'close']
        
        # 데이터 타입 변환 및 정렬 (과거 -> 현재)
        df = df.sort_values('date').reset_index(drop=True)
        cols = ['open', 'high', 'low', 'close']
        df[cols] = df[cols].apply(pd.to_numeric)
        
        return df

    except Exception:
        return pd.DataFrame()
