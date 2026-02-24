# data_loader.py

import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone


# -------------------------
# 일봉 조회 (ka10081)
# -------------------------
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

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=15)

            if response.status_code == 429:
                print(
                    f" 👉 [RATE LIMIT] 429 on {stock_code} "
                    f"(attempt {attempt}/{max_retries}) => sleep {backoff:.1f}s",
                    flush=True
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 20.0)
                continue

            if response.status_code != 200:
                print(
                    f" 👉 [API 에러] 상태코드: {response.status_code}, 상세: {response.text}",
                    flush=True
                )
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

    print(f" 👉 [FAIL] {stock_code} - rate limit or errors exceeded retries", flush=True)
    return pd.DataFrame()


# -------------------------
# KOSPI200 구성종목 조회 (ka10171)
# -------------------------
def get_kospi200_codes(base_url: str, token: str) -> list[str]:
    url = f"{base_url}/api/dostk/idxcomp"

    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10171",
    }

    body = {
        "idx_cd": "201"  # KOSPI200
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

    return [row["stk_cd"].zfill(6) for row in rows if "stk_cd" in row]
