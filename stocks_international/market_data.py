import yfinance as yf
import pandas as pd
from typing import Optional, List

def get_market_data(ticker: str, period: str = "2y") -> Optional[pd.DataFrame]:
    """
    Fetches historical market data for a given ticker using Ticker.history.
    """
    try:
        dat = yf.Ticker(ticker)
        df = dat.history(period=period, auto_adjust=True)
        
        if df.empty:
            return None
        if len(df) < 50: 
            return None 

        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def get_live_price(ticker: str) -> float:
    try:
        data = yf.Ticker(ticker)
        return data.fast_info['last_price']
    except:
        return 0.0

def get_international_tickers() -> List[str]:
    """
    Returns a curated list of top International ADRs (American Depositary Receipts)
    that trade on US Exchanges (NYSE/Nasdaq) and are compatible with yfinance.
    """
    return [
        # Taiwan / Semis
        "TSM", "UMC", "ASX",
        # Europe / Tech / Semi
        "ASML", "SAP", "STM", "ARM", "INFY", 
        # China (Big Tech - High Risk/Reward)
        "BABA", "PDD", "JD", "BIDU", "TCEHY", "NIO", "XPEV", "LI",
        # Latin America
        "NU", "MELI", "PBR", "VALE", "ITUB",
        # Canada
        "SHOP", "CP", "CNI", "BMO", "TD",
        # Pharma / Bio (Global)
        "NVO", "AZN", "SNY", "NVS",
        # Energy / Materials / Mining
        "SHEL", "TTE", "BP", "BHP", "RIO", "SCCO",
        # Japan (ADRs)
        "SONY", "HMC", "TM", "MUFG", "SMFG", "IX"
    ]
