import pandas as pd

import numpy as np

def calculate_technicals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds technical indicators needed for the 'Ceiling Smasher' strategy.
    
    Indicators:
    - SMA 20 (Trend)
    - SMA 50 (Trend)
    - 52-Week High (The Ceiling)
    - RSI (Momentum)
    - Relative Volume (The Fuel)
    - Bollinger Bands (Squeeze detection)
    """
    df = df.copy()
    
    # Defensive fix: Ensure key columns are Series, not DataFrames
    for col in ['High', 'Close', 'Volume']:
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    
    # 1. 52-Week High
    # We use a rolling window of 252 trading days (approx 1 year)
    df['52_Week_High'] = df['High'].rolling(window=252).max()
    
    # 2. Daily Returns & Volatility
    df['Returns'] = df['Close'].pct_change()
    
    # 3. Simple Moving Averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    # 4. Relative Volume (RVOL)
    # Average volume over last 20 days
    df['Avg_Volume_20'] = df['Volume'].rolling(window=20).mean()
    df['RVOL'] = df['Volume'] / df['Avg_Volume_20']
    
    # 5. RSI (14)
    # Manual Calculation or use 'ta' lib if simple
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 6. Bollinger Bands (20, 2)
    std_dev = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (std_dev * 2)
    df['BB_Lower'] = df['SMA_20'] - (std_dev * 2)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['SMA_20']
    
    return df

def analyze_breakout(df: pd.DataFrame) -> dict:
    """
    Analyzes the latest candle to see if it meets 'Ceiling Smasher' criteria.
    Returns a dictionary of metrics and boolean flags.
    """
    if df is None or df.empty:
        return {}
        
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Criteria 1: Near or Breaking Ceiling 
    # Price is within 5% of 52w High OR above it
    dist_to_high = (latest['Close'] - latest['52_Week_High']) / latest['52_Week_High']
    is_breaking_out = latest['Close'] >= latest['52_Week_High'] * 0.98 # Close enough (2%) to be active
    
    # Criteria 2: High Relative Volume
    # We want Volume > 1.5x average
    has_volume = latest['RVOL'] > 1.5
    
    # Criteria 3: Momentum
    # RSI > 55 (Trending up) but ideally not > 85 (unless fully euphoric)
    has_momentum = latest['RSI'] > 55
    
    # Aggression Score (0-100)
    score = 0
    if is_breaking_out: score += 40
    if has_volume: score += 20
    if latest['RSI'] > 60: score += 10
    if latest['Close'] > latest['SMA_20']: score += 10
    if latest['Close'] > latest['SMA_50']: score += 10
    if latest['Volume'] > 1000000: score += 10 # Liquidity check
    
    return {
        "price": latest['Close'],
        "52w_high": latest['52_Week_High'],
        "pct_from_high": dist_to_high * 100,
        "is_breaking_out": is_breaking_out,
        "rvol": latest['RVOL'],
        "rsi": latest['RSI'],
        "score": score
    }
