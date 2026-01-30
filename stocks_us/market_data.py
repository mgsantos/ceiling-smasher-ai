import yfinance as yf
import pandas as pd
import requests
from typing import Optional, List
from io import StringIO

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

def get_sp500_tickers() -> List[str]:
    """Scrapes Wikipedia for the S&P 500 components."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        
        tables = pd.read_html(StringIO(r.text))
        df = tables[0]
        tickers = df['Symbol'].tolist()
        return [t.replace('.', '-') for t in tickers]
    except Exception as e:
        print(f"Error fetching S&P 500: {e}")
        return []

def get_nasdaq100_tickers() -> List[str]:
    """Scrapes Wikipedia for the Nasdaq 100 components."""
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        
        tables = pd.read_html(StringIO(r.text))
        for table in tables:
            if 'Ticker' in table.columns:
                return [t.replace('.', '-') for t in table['Ticker'].tolist()]
            if 'Symbol' in table.columns:
                 return [t.replace('.', '-') for t in table['Symbol'].tolist()]
        return []
    except Exception as e:
        print(f"Error fetching Nasdaq 100: {e}")
        return []
