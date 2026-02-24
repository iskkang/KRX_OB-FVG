# src/data_loader.py

import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone


# =========================================================
# 일봉 조회 (ka10081)
# =========================================================
def get_daily_ohlcv(base_url, token, stock_code, max_retries: int = 5):
    url = f"{base_url}/api/dostk/chart"

    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10081",
    }

    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime("%Y%m%d")

    body = {
        "stk_cd": f"KRX:{stock_code}",
        "base_dt": today_str,
        "upd_stkpc_tp": "1",
    }

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=15)

            if response.status_code == 429:
                print(
                    f" 👉 [RATE LIMIT] 429 on {stock_code} "
                    f"(attempt {attempt}/{max_retries}) => sleep {backoff:.1f}s",
                    flush=True,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 20.0)
                continue

            if response.status_code != 200:
                print(
                    f" 👉 [API 에러] 상태코드: {response.status_code}, 상세: {response.text}",
                    flush=True,
                )
                return pd.DataFrame()

            data = response.json()
            daily_data = data.get("stk_dt_pole_chart_qry", [])

            if not daily_data:
                print(f" 👉 [데이터 없음] {stock_code}", flush=True)
                return pd.DataFrame()

            df = pd.DataFrame(daily_data)
            df = df[["dt", "open_pric", "high_pric", "low_pric", "cur_prc"]]
            df.columns = ["date", "open", "high", "low", "close"]
            df = df.sort_values("date").reset_index(drop=True)

            cols = ["open", "high", "low", "close"]
            df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
            return df

        except Exception as e:
            print(f" 👉 [시스템 에러] {stock_code}: {e}", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 20.0)

    print(f" 👉 [FAIL] {stock_code} retries exceeded", flush=True)
    return pd.DataFrame()


# =========================================================
# KOSPI200 종목 조회 (mockapi 대응 우회 방식)
# =========================================================
def get_kospi200_codes(base_url: str, token: str) -> list[str]:
    """
    mockapi에서는 지수구성종목 API가 없음.
    → KOSPI 전체 종목 조회(ka10050) 후
      KOSPI200에 해당하는 종목만 필터링
    """

    url = f"{base_url}/api/dostk/stklist"

    headers = {
        "content-type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10050",  # 시장별 종목 조회
    }

    body = {
        "mrkt_tp": "0",  # 0 = KOSPI
    }

    response = requests.post(url, headers=headers, json=body, timeout=15)

    if response.status_code != 200:
        raise RuntimeError(
            f"KOSPI 종목 조회 실패: {response.status_code} {response.text}"
        )

    data = response.json()
    rows = data.get("stk_list", [])

    if not rows:
        raise RuntimeError(f"KOSPI 응답 비정상: {data}")

    # 🔹 mockapi에서는 실제 KOSPI200 플래그가 없음
    # 🔹 현실적인 대안: 시가총액 상위 200개를 KOSPI200 proxy로 사용
    df = pd.DataFrame(rows)

    # 필요한 컬럼 방어
    required = {"stk_cd", "mrkt_tot_amt"}
    if not required.issubset(df.columns):
        raise RuntimeError(f"응답 컬럼 부족: {df.columns}")

    df["mrkt_tot_amt"] = pd.to_numeric(df["mrkt_tot_amt"], errors="coerce")
    df = df.dropna(subset=["mrkt_tot_amt"])

    df = df.sort_values("mrkt_tot_amt", ascending=False).head(200)

    return df["stk_cd"].astype(str).str.zfill(6).tolist()
