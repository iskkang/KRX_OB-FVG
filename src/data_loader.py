import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from pykrx import stock

def get_kospi200_codes():
    """
    pykrx의 잦은 날짜 함수 버그를 원천 차단하기 위해,
    어제 날짜부터 하루씩 역순으로 빼면서 시가총액 데이터가 존재하는 '최근 영업일'을 직접 찾습니다.
    """
    KST = timezone(timedelta(hours=9))
    
    # 1. 어제 날짜부터 탐색 시작 (장 마감 시간대 미확정 데이터 회피)
    target_date = datetime.now(KST) - timedelta(days=1)
    
    # 2. 최대 10일 전까지만 거슬러 올라감 (명절 연휴 방어)
    for _ in range(10):
        date_str = target_date.strftime("%Y%m%d")
        
        try:
            # 해당 날짜의 시가총액 데이터 요청
            df = stock.get_market_cap(date_str, market="KOSPI")
            
            # 3. 휴일이 아니라서 데이터가 존재한다면 즉시 200개 추출 후 종료
            if not df.empty:
                codes = df.sort_values("시가총액", ascending=False).head(200).index.tolist()
                return codes
        except Exception:
            pass
            
        # 데이터가 없으면(휴일이면) 하루 전으로 이동
        target_date -= timedelta(days=1)
        
    print("❌ 최근 영업일 데이터를 찾을 수 없습니다.")
    return []

def get_daily_ohlcv(base_url, token, stock_code):
    """
    키움 REST API를 통해 일봉 데이터를 조회합니다.
    """
    url = f"{base_url}/api/dostk/mrkcond" 
    
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10004" # ⚠️ (매우 중요) 첨부문서를 확인해보니 ka10004는 '주식호가' API입니다. 일봉 API ID를 키움증권에서 확인 후 반드시 변경하셔야 합니다.
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
