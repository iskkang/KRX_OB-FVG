import pandas as pd

def check_ob_fvg_signal(df, lookback=20):
    """OB(오더블록) + FVG(공정가치갭) 발생 여부 판별"""
    if df.empty or len(df) < lookback + 5:
        return False, None

    df = df.copy()

    # 1. Bullish Order Block (상승 장악형)
    # 전일 음봉 & 금일 양봉 & 금일 종가가 전일 고가 돌파(장악)
    prev_red = df['close'].shift(1) < df['open'].shift(1)
    curr_green = df['close'] > df['open']
    engulfing = df['close'] > df['high'].shift(1)
    
    df['isOB'] = prev_red & curr_green & engulfing
    
    # 2. FVG (Fair Value Gap)
    # (2봉 전 고가) < (현재 봉 저가) : 갭 발생
    df['hasFVG'] = df['high'].shift(2) < df['low']
    
    # 3. Final Signal
    df['buySignal'] = df['isOB'] & df['hasFVG']
    
    # 최신 봉(오늘 확정된 봉) 기준 확인
    last_idx = df.index[-1]
    
    if df.loc[last_idx, 'buySignal']:
        entry = df['high'].shift(1).loc[last_idx] # 진입가
        sl = df['low'].shift(1).loc[last_idx]     # 손절가
        tp = df['high'].rolling(window=lookback).max().loc[last_idx] # 익절가
        
        return True, (entry, sl, tp)
        
    return False, None
