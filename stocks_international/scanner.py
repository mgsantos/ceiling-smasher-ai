import pandas as pd
from typing import List, Dict
from . import market_data
from . import technicals
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_TICKERS = market_data.get_international_tickers()

def get_market_tickers(scan_type: str = "default") -> List[str]:
    """Returns the list of international tickers."""
    # For international, 'full' currently just means the full ADR list we defined
    return DEFAULT_TICKERS

def scan_tickers(tickers: List[str]) -> List[Dict]:
    """
    Scans a list of tickers and returns those that meet the aggressive criteria.
    Uses threading for speed.
    """
    results = []
    
    print(f"Scanning {len(tickers)} International assets...")
    
    with ThreadPoolExecutor(max_workers=10) as executor: # Lower threads for ADRs (sometimes slower)
        future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
        
        done_count = 0
        total = len(tickers)
        
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            done_count += 1
            if done_count % 10 == 0:
                print(f"Intl Progress: {done_count}/{total}")
                
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                pass

    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def analyze_ticker(ticker: str) -> Dict:
    """Helper to process a single ticker."""
    df = market_data.get_market_data(ticker)
    if df is None:
        return None
        
    df = technicals.calculate_technicals(df)
    analysis = technicals.analyze_breakout(df)
    
    # Filter: Score > 20
    if analysis.get('score', 0) < 20:
        return None
        
    analysis['ticker'] = ticker
    analysis['category'] = 'International' # Explicit tag
    return analysis
