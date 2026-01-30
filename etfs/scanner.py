import pandas as pd
from typing import List, Dict
from . import market_data
from . import technicals
from . import etf_lists
from concurrent.futures import ThreadPoolExecutor, as_completed

def scan_etfs() -> List[Dict]:
    """
    Scans the defined ETF universe and returns potential breakouts.
    """
    tickers = etf_lists.ALL_ETFS
    results = []
    
    print(f"Scanning {len(tickers)} Macro ETFs...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
        
        for future in as_completed(future_to_ticker):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception:
                pass

    # Sort by Score (Desc)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def analyze_ticker(ticker: str) -> Dict:
    """Helper to process a single ticker."""
    df = market_data.get_market_data(ticker)
    if df is None:
        return None
        
    df = technicals.calculate_technicals(df)
    analysis = technicals.analyze_breakout(df)
    
    # Filter: Must not be boring (Score > 20)
    if analysis.get('score', 0) < 20:
        return None
        
    analysis['ticker'] = ticker
    
    # Tagging the category (Helper for UI)
    if ticker in etf_lists.COUNTRIES: analysis['category'] = "Country"
    elif ticker in etf_lists.COMMODITIES: analysis['category'] = "Commodity"
    elif ticker in etf_lists.SECTORS: analysis['category'] = "Sector"
    elif ticker in etf_lists.BONDS_YIELDS: analysis['category'] = "Bond/Yield"
    else: analysis['category'] = "Other"
    
    return analysis
