# data_loader.py

import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

def get_daily_ohlcv(base_url, token, stock_code, max_retries: int = 5):
    url = f"{base_url}/api/dostk/chart"

    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10081"
    }

    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%Y%m%d")

    body = {
        "stk_cd": f"KRX:{stock_code}",
        "base_dt": today_str,
        "upd_stkpc_tp": "1"
    }

# data_loader.py 에 추가

def get_kospi200_codes(base_url: str, token: str) -> list[str]:
    """
    키움 REST API를 통해 KOSPI200 구성 종목 코드 리스트 반환
    """
    url = f"{base_url}/api/dostk/idxcomp"

    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10171",  # 지수 구성종목 조회
    }

    body = {
        "idx_cd": "201"  # KOSPI200 지수 코드
    }

    response = requests.post(url, headers=headers, json=body, timeout=15)

    if response.status_code != 200:
        raise RuntimeError(
            f"KOSPI200 조회 실패: {response.status_code} {response.text}"
        )

    data = response.json()
    rows = data.get("idx_comp_stk", [])

    if not rows:
        raise RuntimeError(f"KOSPI200 응답 비정상: {data}")

    # 종목코드만 추출 (6자리)
    codes = [
        row["stk_cd"].zfill(6)
        for row in rows
        if "stk_cd" in row
    ]

    return codes

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=15)

            # ✅ 레이트리밋(429) => 쉬었다 재시도
            if response.status_code == 429:
                print(f" 👉 [RATE LIMIT] 429 on {stock_code} (attempt {attempt}/{max_retries}) "
                      f"=> sleep {backoff:.1f}s", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 20.0)
                continue

            # 기타 비정상
            if response.status_code != 200:
                print(f" 👉 [API 에러] 상태코드: {response.status_code}, 상세: {response.text}", flush=True)
                return pd.DataFrame()

            data = response.json()
            daily_data = data.get("stk_dt_pole_chart_qry", [])

            if not daily_data:
                print(f" 👉 [데이터 없음] 키움증권 응답: {data}", flush=True)
                return pd.DataFrame()

            df = pd.DataFrame(daily_data)
            df = df[['dt', 'open_pric', 'high_pric', 'low_pric', 'cur_prc']]
            df.columns = ['date', 'open', 'high', 'low', 'close']
            df = df.sort_values('date').reset_index(drop=True)

            cols = ['open', 'high', 'low', 'close']
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            return df

        except Exception as e:
            print(f" 👉 [시스템 에러] {stock_code} 요청 중 오류: {e}", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 20.0)

    # retries exhausted
    print(f" 👉 [FAIL] {stock_code} - rate limit or errors exceeded retries", flush=True)
    return pd.DataFrame()
