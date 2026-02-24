import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import FinanceDataReader as fdr

def get_kospi200_codes():
    """
    해외 IP(GitHub Actions) 차단을 피하기 위해 pykrx 대신 FinanceDataReader를 사용합니다.
    코스피 전 종목을 불러온 뒤 시가총액(Marcap) 상위 200개 종목을 추출합니다.
    """
    try:
        # 코스피 전 종목 데이터 가져오기 (시가총액 포함)
        df = fdr.StockListing('KOSPI')
        
        # 시가총액(Marcap) 기준으로 내림차순 정렬 후 상위 200개 자르기
        top200_df = df.sort_values('Marcap', ascending=False).head(200)
        
        # 종목코드만 리스트로 추출
        codes = top200_df['Code'].tolist()
        return codes
        
    except Exception as e:
        print(f"❌ 종목 코드를 불러오는데 실패했습니다: {e}")
        return []

def get_daily_ohlcv(base_url, token, stock_code):
    """
    키움 REST API 문서(ka10081)를 반영한 일봉 차트 데이터 조회
    """
    url = f"{base_url}/api/dostk/chart" 
    
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10081" # 주식일봉차트조회요청
    }
    
    # 한국 시간 기준 오늘 날짜 구하기
    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%Y%m%d")
    
    body = {
        "stk_cd": stock_code,
        "base_dt": today_str, # 기준일자
        "upd_stkpc_tp": "1"   # 수정주가 1:반영, 0:미반영
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code != 200:
            return pd.DataFrame()

        data = response.json()
        
        # 문서에 명시된 일봉 데이터 리스트 키값
        daily_data = data.get('stk_dt_pole_chart_qry', []) 
        
        if not daily_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(daily_data)
        
        # 문서에 명시된 응답 변수명 매핑
        df = df[['dt', 'open_pric', 'high_pric', 'low_pric', 'cur_prc']]
        df.columns = ['date', 'open', 'high', 'low', 'close']
        
        # 시간순으로 정렬 (과거 데이터가 위로 오도록)
        df = df.sort_values('date').reset_index(drop=True)
        
        # 수치형 데이터로 변환
        cols = ['open', 'high', 'low', 'close']
        df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
        
        return df

    except Exception as e:
        print(f"[{stock_code}] 차트 조회 에러: {e}")
        return pd.DataFrame()
