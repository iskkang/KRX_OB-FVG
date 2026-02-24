import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import FinanceDataReader as fdr

def get_kospi200_codes():
    try:
        df = fdr.StockListing('KOSPI')
        top200_df = df.sort_values('Marcap', ascending=False).head(200)
        codes = top200_df['Code'].tolist()
        return codes
    except Exception as e:
        print(f"❌ 종목 코드를 불러오는데 실패했습니다: {e}")
        return []

def get_daily_ohlcv(base_url, token, stock_code):
    url = f"{base_url}/api/dostk/chart" 
    
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10081" 
    }
    
    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%Y%m%d")
    
    body = {
        "stk_cd": f"KRX:{stock_code}", # CSV 문서 지침에 따라 'KRX:' 접두어 추가
        "base_dt": today_str,
        "upd_stkpc_tp": "1"
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        
        # 1. HTTP 상태 코드가 200(정상)이 아닐 경우 상세 출력
        if response.status_code != 200:
            print(f" 👉 [API 에러] 상태코드: {response.status_code}, 상세: {response.text}")
            return pd.DataFrame()

        data = response.json()
        
        # 2. 키움증권 응답에 데이터 리스트가 없을 경우 전체 응답값 출력
        daily_data = data.get('stk_dt_pole_chart_qry', []) 
        
        if not daily_data:
            print(f" 👉 [데이터 없음] 키움증권 응답: {data}")
            return pd.DataFrame()
            
        df = pd.DataFrame(daily_data)
        
        df = df[['dt', 'open_pric', 'high_pric', 'low_pric', 'cur_prc']]
        df.columns = ['date', 'open', 'high', 'low', 'close']
        df = df.sort_values('date').reset_index(drop=True)
        
        cols = ['open', 'high', 'low', 'close']
        df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
        
        return df

    except Exception as e:
        print(f" 👉 [시스템 에러] 파이썬 실행 중 오류: {e}")
        return pd.DataFrame()
