import asyncio
from ib_insync import *
from typing import List, Dict, Optional
import time
import os
import math
from utils.logger import logger

# Interactive Brokers Connection Details
# Port 7497 is usually Paper Trading, 7496 is Live Trading, 4001 is IB Gateway
IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", 4001))
CLIENT_ID = int(os.getenv("IB_CLIENT_ID", 6))

def connect_ibkr(host=IB_HOST, port=IB_PORT, client_id=CLIENT_ID) -> Optional[IB]:
    """
    Connects to the IBKR TWS or Gateway.
    """
    ib = IB()
    try:
        if not ib.isConnected():
            ib.connect(host, port, clientId=client_id)
        return ib
    except Exception as e:
        print(f"Error connecting to IBKR: {e}")
        return None

def check_connection_status(host=IB_HOST, port=IB_PORT, timeout=2) -> bool:
    """
    Fast check if the IBKR TWS/Gateway port is open and listening.
    Avoids full handshake overhead for status dashboards.
    """
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def get_portfolio() -> List[Dict]:
    """
    Fetches the current live portfolio positions.
    Returns a list of dicts with formatted data.
    """
    ib = connect_ibkr()
    if not ib:
        return []
    
    # 1. Force the Gateway to send account updates immediately
    # We must wait a moment for managedAccounts to be populated
    ib.sleep(0.5) 
    accounts = ib.managedAccounts()
    print(f"Managed Accounts: {accounts}")
    
    preferred_account = os.getenv("IB_ACCOUNT")
    target_account = None

    if preferred_account and preferred_account in accounts:
        target_account = preferred_account
    elif accounts:
        target_account = accounts[0]
    
    if target_account:
        # Subscribe to the target account
        print(f"Subscribing to account: {target_account}")
        logger.info(f"Subscribing to account: {target_account}")
        
        # 1. Request Account Updates (for Cache/Validation) - Non-blocking
        ib.client.reqAccountUpdates(True, target_account)
        
        # 2. Request All Positions (Robust source of truth)
        ib.reqPositions()
    else:
        # Fallback
        print("Warning: No managed accounts found. Attempting default subscription.")
        logger.warning("No managed accounts found. Attempting default subscription.")
        ib.client.reqAccountUpdates(True, "")
        ib.reqPositions()
    
    # 2. Polling Loop: Wait for data to arrive
    # We try 5 times (5 seconds total) to let the data stream in.
    portfolio_items = []
    positions_items = []
    
    print("Waiting for portfolio synchronization...")
    
    for i in range(5):
        ib.waitOnUpdate(timeout=1.0) # Process incoming network messages
        portfolio_items = ib.portfolio()
        positions_items = ib.positions()
        
        # Filter positions for our target account if specified
        if target_account and positions_items:
            positions_items = [p for p in positions_items if p.account == target_account]

        if portfolio_items:
            print(f"Success: Received {len(portfolio_items)} portfolio items.")
            logger.info(f"Success: Received {len(portfolio_items)} portfolio items.")
            break
        elif positions_items:
             print(f"Success: Received {len(positions_items)} positions (via reqPositions).")
             logger.info(f"Success: Received {len(positions_items)} positions (via reqPositions).")
             break
        else:
            print(f" ... attempts {i+1}/5 (No positions yet)")
            
    # 3. If still empty, check if we at least have Cash Balance (Account Values)
    # This proves the connection works, but you truly have 0 positions.
    if not portfolio_items and not positions_items:
        # Filter for the specific account
        acc_vals = ib.accountValues()
        if target_account:
            acc_vals = [v for v in acc_vals if v.account == target_account]
            
        if acc_vals:
            print("Connected successfully! Account data found, but Portfolio is empty (0 positions held).")
            logger.info("Connected successfully! Account data found, but Portfolio is empty.")
            # Optional: Print Cash Balance to prove it works
            cash = next((v for v in acc_vals if v.tag == 'TotalCashValue'), None)
            if cash: print(f"Account Cash: {cash.value} {cash.currency}")
        else:
            print("Portfolio failed to sync. (Check Gateway 'Trusted IPs' or Restart Gateway)")
            logger.error("Portfolio failed to sync. Check Gateway.")
        
        ib.disconnect()
        return []
    
    results = []
    
    # Prefer PortfolioItems (richer data) if available, otherwise use Positions
    if portfolio_items:
        for item in portfolio_items:
            # Calculate pct_return safely
            cost_basis = item.averageCost * item.position
            pnl = item.unrealizedPNL
            pct_return = (pnl / cost_basis * 100) if cost_basis != 0 else 0.0
            
            # Format Ticker for Options
            ticker_display = item.contract.symbol
            if item.contract.secType == 'OPT':
                try:
                    # Format: 20270115 -> 15JAN27
                    from datetime import datetime
                    exp_date = item.contract.lastTradeDateOrContractMonth
                    if len(exp_date) == 8:
                        dt = datetime.strptime(exp_date, "%Y%m%d")
                        exp_str = dt.strftime("%d%b%y").upper()
                    else:
                        exp_str = exp_date
                    
                    ticker_display = f"{item.contract.symbol} {exp_str} {item.contract.strike} {item.contract.right}"
                except:
                    ticker_display = f"{item.contract.symbol} {item.contract.lastTradeDateOrContractMonth} {item.contract.strike} {item.contract.right}"

            # Try to get a descriptive name if available (often requires reqContractDetails, but let's check basic fields)
            # For PortfolioItems, we might have it.
            description = item.contract.localSymbol
            if item.contract.primaryExchange:
                 description += f" ({item.contract.primaryExchange})"

            results.append({
                "ticker": ticker_display,
                "description": description, 
                "secType": item.contract.secType,
                "currency": item.contract.currency,
                "position": item.position,
                "market_price": item.marketPrice,
                "avg_cost": item.averageCost,
                "market_value": item.marketValue,
                "unrealized_pnl": item.unrealizedPNL,
                "pct_return": pct_return
            })
    elif positions_items:
        # Fallback to Positions objects (Basic Data Only)
        print("Note: Fetched positions. Portfolio Sync incomplete, showing basic data only.")
        
        for p in positions_items:
            # Format Ticker for Options
            ticker_display = p.contract.symbol
            if p.contract.secType == 'OPT':
                try:
                    from datetime import datetime
                    exp_date = p.contract.lastTradeDateOrContractMonth
                    if len(exp_date) == 8:
                        dt = datetime.strptime(exp_date, "%Y%m%d")
                        exp_str = dt.strftime("%d%b%y").upper()
                    else:
                        exp_str = exp_date
                    ticker_display = f"{p.contract.symbol} {exp_str} {p.contract.strike} {p.contract.right}"
                except:
                    ticker_display = f"{p.contract.symbol} {p.contract.lastTradeDateOrContractMonth} {p.contract.strike} {p.contract.right}"

            results.append({
                "ticker": ticker_display,
                "description": p.contract.localSymbol,
                "secType": p.contract.secType,
                "currency": p.contract.currency,
                "position": p.position,
                "market_price": 0.0, 
                "avg_cost": p.avgCost, 
                "market_value": 0.0,
                "unrealized_pnl": 0.0,
                "pct_return": 0.0
            })
        
    ib.disconnect()
    return results

if __name__ == "__main__":
    # Test
    print("--- Testing IBKR Connection ---")
    pf = get_portfolio()
    for p in pf:
        print(p)
