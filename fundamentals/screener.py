import requests
import pandas as pd
import os
from typing import List, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich import print
from stocks_us import market_data as us_data
from stocks_us import technicals as us_tech

import logging
import sys

# Configure logging to file and stdout
logger = logging.getLogger("fundamentals")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # File Handler
    fh = logging.FileHandler("logs/app_2026-02-01.log")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

FMP_BASE_URL = "https://financialmodelingprep.com/stable"

def get_api_key():
    key = os.environ.get("FMP_API_KEY")
    if not key:
        print("[red]Error: FMP_API_KEY not found in .env[/red]")
        return None 
    return key

# --- STRATEGY DEFINITIONS ---
STRATEGIES = {
    "VALUE": {
        "description": "Deep Value (The Golden Filter)",
        "screener_params": {
            "marketCapMoreThan": 1_000_000_000, # Large/Mid Cap only
            "priceMoreThan": 5,
            "volumeMoreThan": 50_000,
            "isEtf": "false",
            "isActivelyTrading": "true",
            "limit": 1000
        },
        "filters": {
            "max_ev_ebitda": 8.0,
            "max_debt_equity": 0.6,
            "min_gross_margin": 0.20,
            "min_fcf_yield": 0.08
        }
    },
    "GROWTH": {
        "description": "Hyper-Velocity Growth (Strict)",
        "screener_params": {
            "marketCapMoreThan": 500_000_000,
            "marketCapLowerThan": 50_000_000_000,
            "priceMoreThan": 5,
            "volumeMoreThan": 100_000,
            "isEtf": "false",
            "isActivelyTrading": "true",
            "limit": 1000,
            "revenueGrowthMoreThan": 20,
            "grossProfitGrowthMoreThan": 15,
            "betaMoreThan": 1.2
        },
        "filters": {
            "max_ev_ebitda": 35.0,   # Allow higher multiple for true rockets
            "max_debt_equity": 0.8,  # Slightly tighter debt rule
            "min_gross_margin": 0.40,
            "min_fcf_yield": 0.0
        }
    },
    "MICROCAP": {
        "description": "Undervalued Microcap (The Moonshots)",
        "screener_params": {
            "marketCapLowerThan": 500_000_000,
            "marketCapMoreThan": 50_000_000,
            "priceMoreThan": 2,
            "volumeMoreThan": 20_000,
            "isEtf": "false",
            "isActivelyTrading": "true",
            "limit": 1000
        },
        "filters": {
            "max_ev_ebitda": 10.0,
            "max_debt_equity": 0.5,
            "min_gross_margin": 0.15,
            "min_fcf_yield": 0.05
        }
    }
}

def fetch_universe(strategy_name: str, api_key: str) -> List[Dict]:
    """Stage 1: Get list based on Strategy Params from FMP Stable Screener"""
    params = STRATEGIES[strategy_name]["screener_params"]
    params["apikey"] = api_key
    params["exchange"] = "NYSE,NASDAQ"
    params["limit"] = "5000"
    
    print(f"[blue]🌍 Stage 1: Fetching {strategy_name} universe...[/blue]")
    try:
        # Using the _make_api_request helper isn't strictly necessary for the single screener call,
        # but good for consistency. However, screener parameters are passed differently.
        # So we'll stick to direct requests with basic error handling here.
        url = f"{FMP_BASE_URL}/company-screener"
        res = requests.get(url, params=params)
        
        if res.status_code != 200:
             print(f"[red]API Error {res.status_code}: {res.text}[/red]")
             return []

        data = res.json()
        if isinstance(data, dict) and "Error Message" in data:
            print(f"[red]API Error: {data['Error Message']}[/red]")
            return []
            
        print(f"[green]✅ Found {len(data)} candidates.[/green]")
        return data
    except Exception as e:
        print(f"[red]Universe Error: {e}[/red]")
        return []
def _make_api_request(url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
    """
    Helper to make API requests with rate limit handling (429).
    Retries after 60 seconds if rate limit is hit.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.get(url, params=params)
            if res.status_code == 429:
                print(f"[yellow]⚠️ Rate Limit Hit (429). Sleeping 60s... (Attempt {attempt+1}/{max_retries})[/yellow]")
                time.sleep(60)
                continue
            return res
        except requests.exceptions.RequestException as e:
            print(f"[red]Request Error: {e}[/red]")
            return None
    
    print(f"[red]❌ Max retries exceeded for {url}[/red]")
    return None
def fetch_financial_data(symbol: str, api_key: str, needs_growth: bool = False) -> Optional[Dict]:
    """
    Fetches raw financial data for a ticker without applying filters.
    Returns a dictionary of metrics if successful, None otherwise.
    """
    try:
        data = {"Symbol": symbol}
        
        # 1. Growth (Optional but prioritized if needed for velocity checks)
        if needs_growth:
            growth_url = f"https://financialmodelingprep.com/api/v3/financial-growth/{symbol}?limit=1&apikey={api_key}"
            res_g = _make_api_request(growth_url)
            if not res_g or res_g.status_code != 200: return None
            
            g_data = res_g.json()
            if not g_data: return None
            
            data["Growth"] = g_data[0] # Store raw dict

        # 2. Ratios (Valuation, Debt, Margin)
        ratios_url = f"{FMP_BASE_URL}/ratios-ttm?symbol={symbol}&limit=1&apikey={api_key}"
        res = _make_api_request(ratios_url)
        if not res or res.status_code != 200: return None
        
        r_data = res.json()
        if not r_data: return None
        data["Ratios"] = r_data[0]

        # 3. Key Metrics (FCF Yield)
        metrics_url = f"{FMP_BASE_URL}/key-metrics-ttm?symbol={symbol}&apikey={api_key}"
        res_m = _make_api_request(metrics_url)
        if not res_m or res_m.status_code != 200: return None
        
        m_data = res_m.json()
        if m_data:
            data["Metrics"] = m_data[0]
        else:
            data["Metrics"] = {} # Empty dict if missing, rather than None to avoid crashes

        return data

    except Exception as e:
        # print(f"[red]Err {symbol}: {e}[/red]")
        return None

def check_strategy_filters(data: Dict, filters: Dict) -> Optional[Dict]:
    """
    Checks if the fetched data passes the specific filters.
    Returns a formatted result dictionary if passed, None if rejected.
    """
    try:
        symbol = data["Symbol"]
        ratios = data["Ratios"]
        metrics = data["Metrics"]
        growth = data.get("Growth", {})

        # A. Growth Checks (if applicable)
        rev_growth_val = None
        if "min_revenue_growth" in filters:
            if not growth: return None
            
            rev_growth = growth.get('revenueGrowth', 0)
            if rev_growth < filters['min_revenue_growth']: return None
            rev_growth_val = round(rev_growth * 100, 1)

            ni_growth = growth.get('netIncomeGrowth', 0)
            if ni_growth < filters.get('min_net_income_growth', 0): return None

        # B. Ratio Checks
        # 1. EV / EBITDA
        ev_ebitda = ratios.get('enterpriseValueMultipleTTM')
        if ev_ebitda is None or ev_ebitda > filters['max_ev_ebitda'] or ev_ebitda <= 0: return None

        # 2. Debt / Equity
        debt_equity = ratios.get('debtToEquityRatioTTM')
        if debt_equity is None or debt_equity > filters['max_debt_equity']: return None
            
        # 3. Gross Margin
        gross_margin = ratios.get('grossProfitMarginTTM')
        if gross_margin is None or gross_margin < filters['min_gross_margin']: return None

        # C. Metric Checks
        fcf_yield = metrics.get('freeCashFlowYieldTTM', 0.0)
        # Handle case where metric is None (if empty dict passed)
        if fcf_yield is None: fcf_yield = 0.0

        if fcf_yield < filters['min_fcf_yield']: return None

        # Formatting Result
        result = {
            "Symbol": symbol,
            "EV/EBITDA": round(ev_ebitda, 2),
            "Debt/Equity": round(debt_equity, 2),
            "Gross Margin": f"{round(gross_margin * 100, 1)}%",
            "FCF Yield": f"{round(fcf_yield * 100, 1)}%",
            "raw_fcf": fcf_yield
        }
        
        if rev_growth_val is not None:
             result["Growth"] = f"{rev_growth_val}%"
             
        return result

    except Exception as e:
        # logger.error(f"Filter check error for {data['Symbol']}: {e}")
        return None

def run_consolidated_strategies(modes: List[str]):
    """
    Runs multiple strategies in parallel with deduplicated API calls.
    """
    valid_modes = [m.upper() for m in modes if m.upper() in STRATEGIES]
    if not valid_modes:
        print(f"[red]No valid modes selected. Input: {modes} | Avail: {list(STRATEGIES.keys())}[/red]")
        return
        
    api_key = get_api_key()
    if not api_key: return

    print(f"\n[bold blue]🚀 STARTING CONSOLIDATED SCAN: {', '.join(valid_modes)}[/bold blue]")
    logger.info(f"Phase 1: Starting Fundamentals Screen ({valid_modes})")

    # 1. Deduplicate Universe
    unique_symbols = set()
    for mode in valid_modes:
        u = fetch_universe(mode, api_key)
        if u:
            unique_symbols.update([x['symbol'] for x in u])
            
    if not unique_symbols:
        logger.error("Phase 1 Failed: No candidates found.")
        return
        
    print(f"[blue]🔍 Analyzing {len(unique_symbols)} unique candidates...[/blue]")
    logger.info(f"Phase 2: Deep Dive into {len(unique_symbols)} unique candidates")

    # 2. Parallel Processing
    # Check if ANY strategy needs growth data to optimize fetching
    needs_growth = any("min_revenue_growth" in STRATEGIES[m]['filters'] for m in valid_modes)
    
    results = {m: [] for m in valid_modes}
    
    def process_symbol(sym):
        # Fetch Data Once
        data = fetch_financial_data(sym, api_key, needs_growth)
        if not data: return None
        
        matches = {}
        for mode in valid_modes:
            res = check_strategy_filters(data, STRATEGIES[mode]['filters'])
            if res:
                matches[mode] = res
                
        return matches if matches else None

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(process_symbol, sym): sym for sym in unique_symbols}
        
        count = 0
        for future in as_completed(future_map):
            count += 1
            if count % 50 == 0:
                msg = f"Progress: analyzed {count}/{len(unique_symbols)}..."
                print(msg)
                logger.info(msg)
            
            res_matches = future.result()
            if res_matches:
                for m, val in res_matches.items():
                    print(f"[green]💰 HIT [{m}]: {val['Symbol']} ({val['EV/EBITDA']}x)[/green]")
                    results[m].append(val)

    # 3. Phase 3: Technical Analysis (Enrichment)
    # Collect all unique survivors across strategies
    all_survivors = {}
    for mode, items in results.items():
        for item in items:
            all_survivors[item["Symbol"]] = item

    if not all_survivors:
        logger.warning("Phase 3 Skipped: No survivors found.")
        print("[yellow]No stocks passed fundamentals. Skipping Technicals.[/yellow]")
        save_consolidated_report(results)
        return

    print(f"\n[blue]📈 Phase 3: Technical Analysis on {len(all_survivors)} survivors...[/blue]")
    logger.info(f"Phase 3: Running Technicals on {len(all_survivors)} stocks")

    def process_technicals(item):
        sym = item["Symbol"]
        try:
            # Fetch 2y history for robust technicals
            df = us_data.get_market_data(sym, period="2y")
            if df is None or df.empty: return None
            
            # Calculate Indicators
            df = us_tech.calculate_technicals(df)
            metrics = us_tech.analyze_breakout(df)
            
            return {
                "Symbol": sym,
                "Price": f"${metrics['price']:.2f}",
                "RSI": f"{metrics['rsi']:.0f}",
                "RVOL": f"{metrics['rvol']:.1f}x",
                "Score": metrics['score'],
                "Dist52W": f"{metrics['pct_from_high']:.1f}%"
            }
        except Exception as e:
            # logger.warning(f"Tech Error {sym}: {e}")
            return None

    # Run Technicals in Parallel
    tech_data_map = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(process_technicals, item): item["Symbol"] for item in all_survivors.values()}
        
        count = 0
        for future in as_completed(future_map):
            count += 1
            if count % 10 == 0: print(f"Technicals: {count}/{len(all_survivors)}...")
            
            res = future.result()
            if res:
                tech_data_map[res["Symbol"]] = res
                print(f"[cyan] {res['Symbol']}: RSI {res['RSI']} | Score {res['Score']}[/cyan]")

    # Merge Technicals back into results
    for mode in results:
        for item in results[mode]:
            sym = item["Symbol"]
            if sym in tech_data_map:
                item.update(tech_data_map[sym])
            else:
                # Fill with N/A if technicals failed
                item["Price"] = "N/A"
                item["RSI"] = "-"
                item["RVOL"] = "-"
                item["Score"] = 0
                item["Dist52W"] = "-"

    # 4. Save Consolidated Report
    save_consolidated_report(results)

def save_consolidated_report(results: Dict[str, List[Dict]]):
    """Saves a multi-strategy report."""
    try:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"fundamentals_consolidated_{date_str}.md"
        report_dir = "output"
        if not os.path.exists(report_dir): os.makedirs(report_dir)
        filepath = os.path.join(report_dir, filename)

        with open(filepath, "w") as f:
            f.write(f"# 💎 Consolidated Fundamental Scan\n")
            f.write(f"**Date:** {date_str}\n\n")
            
            for mode, items in results.items():
                f.write(f"## Strategy: {mode}\n")
                f.write(f"_{STRATEGIES[mode]['description']}_\n\n")
                if not items:
                    f.write("_No matches found._\n\n")
                    continue
                    
                # Sort by Technical Score (descending) if available, else EV/EBITDA
                if "Score" in items[0]:
                    items.sort(key=lambda x: x.get('Score', 0), reverse=True)
                else:
                    items.sort(key=lambda x: x['EV/EBITDA'])
                
                # LIMIT TO TOP 20 PER STRATEGY based on User request to reduce noise
                top_items = items[:20]
                
                df = pd.DataFrame(top_items)
                
                base_cols = ["Symbol", "Price", "Score", "RSI", "RVOL", "Dist52W", "EV/EBITDA", "Debt/Equity", "Gross Margin", "FCF Yield"]
                if "Growth" in df.columns:
                     cols = ["Symbol", "Growth"] + base_cols[1:]
                else:
                     cols = base_cols
                
                # Filter cols that actually exist in DF
                valid_cols = [c for c in cols if c in df.columns]

                f.write(df[valid_cols].to_markdown(index=False))
                f.write("\n\n")
                
        print(f"\n[bold green]📄 Consolidated Report saved to: {os.path.abspath(filepath)}[/bold green]")

    except Exception as e:
        print(f"[red]Error saving report: {e}[/red]")

# Backward compatibility alias
def run_strategy(mode: str = "VALUE"):
    run_consolidated_strategies([mode])
