import pandas as pd
from typing import List, Dict
from . import market_data
from . import technicals
from concurrent.futures import ThreadPoolExecutor, as_completed

# A "Starter Pack" of high-beta / interesting tickers to scan by default
DEFAULT_TICKERS = [
    # Big Tech / Momentum
    "NVDA", "TSLA", "AMD", "META", "NFLX", "AMZN", "MSFT", "GOOGL", "AAPL",
    # Crypto Proxies / High Vol
    "COIN", "MSTR", "MARA", "RIOT", "CLSK",
    # Semiconductors
    "SMCI", "AVGO", "ARM", 
    # Growth / Speculative
    "PLTR", "SOFI", "UPST", "AFRM", "CVNA",
    # Leveraged ETFs (The real juice)
    "TQQQ", "SOXL", "NVDL", "FNGU"
]

def get_market_tickers(scan_type: str = "default") -> List[str]:
    """Returns the list of tickers based on scan type."""
    if scan_type == "full":
        print("Fetching S&P 500 and Nasdaq 100 lists...")
        sp500 = market_data.get_sp500_tickers()
        nasdaq = market_data.get_nasdaq100_tickers()
        combined = list(set(sp500 + nasdaq + DEFAULT_TICKERS)) # Dedup
        print(f"Total Unique Assets to Scan: {len(combined)}")
        return combined
    else:
        return DEFAULT_TICKERS

def scan_tickers(tickers: List[str]) -> List[Dict]:
    """
    Scans a list of tickers and returns those that meet the aggressive criteria.
    Uses threading for speed.
    """
    results = []
    
    print(f"Scanning {len(tickers)} assets for breakouts...")
    
    # Increased workers for larger lists, but be careful of rate limits
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
        
        # Simple progress tracking (print a dot every 10 done)
        done_count = 0
        total = len(tickers)
        
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            done_count += 1
            if done_count % 50 == 0:
                print(f"Progress: {done_count}/{total}")
                
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                # print(f"Failed {ticker}: {e}") # Reduce noise
                pass

    # Sort by Score (Highest first)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def analyze_ticker(ticker: str) -> Dict:
    """Helper to process a single ticker."""
    df = market_data.get_market_data(ticker)
    if df is None:
        return None
        
    df = technicals.calculate_technicals(df)
    analysis = technicals.analyze_breakout(df)
    
    # Filter: Must not be boring
    # We only return it if it has some sign of life (Score > 20)
    if analysis.get('score', 0) < 20:
        return None
        
    analysis['ticker'] = ticker
    return analysis
