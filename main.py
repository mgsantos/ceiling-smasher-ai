import argparse
import sys
import warnings
# Suppress all warnings to keep the console clean (e.g. urllib3 SSL, Google Auth FutureWarnings)
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
import os

# Load Environment Variables first
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich import box
from rich.markdown import Markdown
import os
import datetime

# Sub-modules (Packages)
# Sub-modules (Packages)
from stocks_us import scanner as us_scanner
from stocks_international import scanner as intl_scanner
from etfs import scanner as etf_scanner
from ai import analyst as ai_analyst
from broker import ibkr
from utils.logger import logger


console = Console()

def main():
    logger.info("Application Started (CLI)")
    parser = argparse.ArgumentParser(description="Ceiling Smasher AI - Hedge Fund Analyst")
    parser.add_argument("--scan", action="store_true", help="Run the Full Market Scan (Stocks + ETFs)")
    parser.add_argument("--portfolio", action="store_true", help="Fetch Live Portfolio from IBKR")
    parser.add_argument("--stocks", action="store_true", help="Run only Stock Scan")
    parser.add_argument("--etfs", action="store_true", help="Run only ETF Scan")
    parser.add_argument("--full", action="store_true", help="Use Full Market list for stocks (S&P 500 + Nasdaq)")
    parser.add_argument("--ai", action="store_true", help="Ask the Hedge Fund Analyst for high-conviction plays")
    parser.add_argument("--save-report", action="store_true", help="Save the output as a Markdown report in output/")
    parser.add_argument("--alpha-toolkit", action="store_true", help="Fetch Asymmetric Information (Alpha Toolkit)")
    parser.add_argument("--review-report", type=str, help="Run Portfolio Manager on an existing report file")
    parser.add_argument("--pm-model", type=str, default="gemini", choices=["gemini", "grok"], help="Choose the AI model for PM (gemini or grok)")
    
    args = parser.parse_args()
    
    # NEW: Portfolio Manager Review Mode
    if args.review_report:
        if not os.path.exists(args.review_report):
            console.print(f"[bold red]❌ Report file not found: {args.review_report}[/bold red]")
            return

        console.print(f"[bold blue]=== PORTFOLIO MANAGER: REVIEWING REPORT ===[/bold blue]")
        console.print(f"📄 Reading: {args.review_report}")
        console.print(f"🧠 Model: {args.pm_model.upper()}")
        
        with open(args.review_report, "r", encoding="utf-8") as f:
            report_content = f.read()
            
        # Fetch Live Portfolio
        console.print("\n[bold blue]=== CONNECTING TO IBKR (TWS/GATEWAY) ===[/bold blue]")
        portfolio = ibkr.get_portfolio()
        
        # Load Alpha Toolkit Data (if available) for PM Review
        alpha_toolkit_data = "No asymmetric data available."
        import glob
        try:
            at_files = glob.glob(f"output/alpha_toolkit_*.md")
            if at_files:
                latest_at = max(at_files, key=os.path.getctime)
                with open(latest_at, "r", encoding="utf-8") as f:
                    alpha_toolkit_data = f.read()
                console.print(f"\n[bold purple]>>> ALPHA TOOLKIT DATA LOADED: {os.path.basename(latest_at)}[/bold purple]")
        except: pass
        
        # Display Portfolio
        if not portfolio:
            console.print("[red]Could not fetch portfolio (or empty). Is TWS running?[/red]")
        else:
            p_table = Table(title=f"💼 LIVE PORTFOLIO ({len(portfolio)} Positions)", box=box.ROUNDED, style="bold white")
            p_table.add_column("Ticker", style="cyan")
            p_table.add_column("Type", style="magenta")
            p_table.add_column("Pos", justify="right")
            p_table.add_column("Avg Cost", justify="right")
            
            for p in portfolio:
                p_table.add_row(
                    p['ticker'],
                    p['secType'],
                    str(p['position']),
                    f"${p['avg_cost']:.2f}"
                )
            console.print(p_table)

        # Run PM Agent
        console.print(f"\n[bold white on blue]>>> AGENT 4: PORTFOLIO MANAGER ({args.pm_model.upper()})[/bold white on blue]")
        
        if args.pm_model == "grok":
            analysis_pm = ai_analyst.execute_portfolio_manager_grok(portfolio, report_content, alpha_toolkit_data=alpha_toolkit_data)
        else:
            analysis_pm = ai_analyst.execute_portfolio_manager(portfolio, report_content, alpha_toolkit_data=alpha_toolkit_data)
            
        md_pm = Markdown(analysis_pm)
        console.print(md_pm)
        console.print("-" * 50)
        return

        console.print("-" * 50)
        return

    # NEW: Alpha Toolkit Data Intake
    if args.alpha_toolkit:
        console.print("[bold purple]=== ALPHA TOOLKIT: ASYMMETRIC INFORMATION ===[/bold purple]")
        logger.info("Phase 0: Fetching Alpha Toolkit Data")
        
        analysis_alpha_toolkit = ai_analyst.analyze_alpha_toolkit()
        
        console.print(Markdown(analysis_alpha_toolkit))
        
        # Save independent report for Alpha Toolkit
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            filename = f"{output_dir}/alpha_toolkit_{timestamp}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(analysis_alpha_toolkit)
            
            console.print(f"\n[bold green]✅ Alpha Toolkit Report saved to: {filename}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]❌ Failed to save report: {e}[/bold red]")
            
            console.print(f"\n[bold green]✅ Alpha Toolkit Report saved to: {filename}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]❌ Failed to save report: {e}[/bold red]")
            
        # Do NOT return here. Allow falling through to scanning/AI if flags are set.


    if not args.scan and not args.stocks and not args.etfs and not args.portfolio and not args.ai:
        console.print("[yellow]Usage: python main.py --scan | --portfolio | --stocks | --etfs [--full] [--ai] | --alpha-toolkit[/yellow]")
        sys.exit(0)
        
    all_results = []
    
    # AI: Launch Independent Agents (Parallel with Scanners)
    ai_executor = None
    ai_futures = {}
    
    if args.ai:
        console.print("[bold yellow]🚀 Launching Independent AI Agents (Google & X) in background...[/bold yellow]")
        logger.info("Phase 2: Launching Independent Agents (Google & X)")
        import concurrent.futures
        ai_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        ai_futures['google'] = ai_executor.submit(ai_analyst.analyze_ideas_from_google)
        ai_futures['x'] = ai_executor.submit(ai_analyst.analyze_ideas_from_x)
    
    # 0. Portfolio Scan (IBKR)
    if args.portfolio:
        logger.info("Phase 0: Fetching Portfolio")
        console.print("[bold blue]=== CONNECTING TO IBKR (TWS/GATEWAY) ===[/bold blue]")
        portfolio = ibkr.get_portfolio()
        
        if not portfolio:
            console.print("[red]Could not fetch portfolio. Is TWS running?[/red]")
        else:
            p_table = Table(title=f"💼 LIVE PORTFOLIO ({len(portfolio)} Positions)", box=box.ROUNDED, style="bold white")
            p_table.add_column("Ticker", style="cyan")
            p_table.add_column("Type", style="magenta")
            p_table.add_column("Pos", justify="right")
            p_table.add_column("Avg Cost", justify="right")
            
            for p in portfolio:
                p_table.add_row(
                    p['ticker'],
                    p['secType'],
                    str(p['position']),
                    f"${p['avg_cost']:.2f}"
                )
                
            console.print(p_table)
            
    # 1. Stocks Scan (US & Intl)
    if args.scan or args.stocks:
        logger.info("Phase 1: Scanning Stocks")
        console.print("[bold green]=== SCANNING US STOCKS ===[/bold green]")
        scan_type = "full" if args.full else "default"
        
        # US
        us_tickers = us_scanner.get_market_tickers(scan_type)
        us_results = us_scanner.scan_tickers(us_tickers)
        all_results.extend(us_results)
        
        # International
        console.print("\n[bold green]=== SCANNING INTERNATIONAL STOCKS (ADRs) ===[/bold green]")
        intl_tickers = intl_scanner.get_market_tickers(scan_type)
        intl_results = intl_scanner.scan_tickers(intl_tickers)
        all_results.extend(intl_results)
        
    # 2. ETFs Scan
    if args.scan or args.etfs:
        logger.info("Phase 1b: Scanning ETFs")
        console.print("\n[bold blue]=== SCANNING GLOBAL MACRO ETFs ===[/bold blue]")
        etf_results = etf_scanner.scan_etfs()
        all_results.extend(etf_results)
        
    if not all_results:
        console.print("[bold red]No opportunities found.[/bold red]")
        return
        
    # Sort ALL results by score for the master table
    all_results.sort(key=lambda x: x['score'], reverse=True)

    # Display Master Table
    table = Table(title="🔥 CEILING SMASHER: MASTER PORTFOLIO 🔥", box=box.HEAVY_EDGE, style="bold white")
    
    table.add_column("Asset", style="cyan", justify="center")
    table.add_column("Type", style="magenta")
    table.add_column("Price", style="green")
    table.add_column("Dist 52wH", justify="right")
    table.add_column("RVOL", justify="right")
    table.add_column("RSI", justify="right")
    table.add_column("Score", style="bold yellow", justify="right")
    
    for r in all_results:
        # Determine category/type
        asset_type = r.get('category', 'Stock')
        
        dist = f"{r['pct_from_high']:.2f}%"
        if r['pct_from_high'] >= 0: dist = f"[bold green]🚀 +{dist}[/bold green]"
        elif r['pct_from_high'] > -5: dist = f"[yellow]{dist}[/yellow]"
        else: dist = f"[red]{dist}[/red]"
        
        rvol_style = "[bold green]" if r['rvol'] > 1.5 else "[white]"
        
        table.add_row(
            r['ticker'],
            asset_type,
            f"${r['price']:.2f}",
            dist,
            f"{rvol_style}{r['rvol']:.1f}x[/]",
            f"{r['rsi']:.0f}",
            str(r['score'])
        )
        
    console.print(table)
    
    # 3. AI Analysis
    if args.ai:
        console.print("\n[bold cyan]🤖 SUMMONING THE INVESTMENT COUNCIL...[/bold cyan]")
        logger.info("Phase 3: Convening Investment Council (Agents 1 & 2)")
        
        # Submit Dependant Agents (1 & 2) that needed the Table
        console.print("[yellow]   ... Deploying Agents 1 (Alpha) and 2 (Value) with Scanner Data ...[/yellow]")
        
        ai_futures['alpha'] = ai_executor.submit(ai_analyst.analyze_concentrated_alpha, table)
        ai_futures['value'] = ai_executor.submit(ai_analyst.analyze_deep_value, table)
        
        # Wait for all results
        analysis_alpha = ai_futures['alpha'].result()
        analysis_value = ai_futures['value'].result()
        analysis_google = ai_futures['google'].result()
        analysis_x = ai_futures['x'].result()
        
        ai_executor.shutdown()

        # 1. Concentrated Alpha Agent
        console.print("\n[bold magenta]>>> AGENT 1: CONCENTRATED ALPHA (Macro/Growth)[/bold magenta]")
        md_alpha = Markdown(analysis_alpha)
        console.print(md_alpha)
        console.print("-" * 50)
        
        # 2. Deep Value Agent
        console.print("\n[bold yellow]>>> AGENT 2: DEEP VALUE (Contrarian/Capital Cycle)[/bold yellow]")
        md_value = Markdown(analysis_value)
        console.print(md_value)
        console.print("-" * 50)

        # 🚀 Agent Ideas from Google
        console.print("\n[bold cyan]>>> AGENT IDEAS FROM GOOGLE (Wealth Multiplier)[/bold cyan]")
        md_google = Markdown(analysis_google)
        console.print(md_google)
        console.print("-" * 50)

        # 🧠 Agent Ideas from X
        console.print("\n[bold white on black]>>> AGENT IDEAS FROM X (X Platform Intelligence)[/bold white on black]")
        md_x = Markdown(analysis_x)
        console.print(md_x)
        console.print("-" * 50)

        # 3. Extract Tickers for Red Team (from Agents 1, 2, Google, and X)
        logger.info("Phase 4: Red Team Vetting Started")
        tickers = []
        tickers.extend(ai_analyst.extract_tickers_from_analysis(analysis_alpha))
        tickers.extend(ai_analyst.extract_tickers_from_analysis(analysis_value))
        tickers.extend(ai_analyst.extract_tickers_from_analysis(analysis_google))
        tickers.extend(ai_analyst.extract_tickers_from_analysis(analysis_x))
        tickers = list(set(tickers)) # Dedupe

        if tickers:
            console.print(f"\n[bold red]>>> ACTIVATING RED TEAM ON: {', '.join(tickers)}[/bold red]")
            analysis_red = ai_analyst.analyze_red_team(tickers)
            md_red = Markdown(analysis_red)
            console.print(md_red)
            console.print("-" * 50)
        else:
            analysis_red = "No tickers found to vet."
            console.print("\n[bold red]>>> RED TEAM STANDING BY (No Targets Acquired)[/bold red]")
        logger.info("Phase 4 Complete.")

        # 4a. Load Alpha Toolkit Data (if available)
        alpha_toolkit_data = "No asymmetric data available."
        import glob
        try:
            at_files = glob.glob(f"output/alpha_toolkit_*.md")
            if at_files:
                latest_at = max(at_files, key=os.path.getctime)
                with open(latest_at, "r", encoding="utf-8") as f:
                    alpha_toolkit_data = f.read()
                console.print(f"\n[bold purple]>>> ALPHA TOOLKIT DATA LOADED: {os.path.basename(latest_at)}[/bold purple]")
            else:
                console.print(f"\n[bold yellow]>>> ALPHA TOOLKIT: No recent data found. Proceeding without.[/bold yellow]")
        except Exception as e:
            logger.error(f"Failed to load Alpha Toolkit data: {e}")

        # 4. The Portfolio Manager (CIO)
        logger.info("Phase 5: CIO Execution Decision")
        console.print("\n[bold red on white]>>> AGENT 3: THE CIO (Final Execution Decision)[/bold red on white]")
        analysis_cio = ai_analyst.execute_portfolio_strategy(
            table, 
            analysis_alpha, 
            analysis_value, 
            analysis_red, 
            analysis_google, 
            analysis_x,
            alpha_toolkit_data=alpha_toolkit_data
        )
        md_cio = Markdown(analysis_cio)
        console.print(md_cio)
        console.print("-" * 50)
        logger.info("Analysis Complete.")

    # 4. Save Report Logic
    if args.save_report:
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            filename = f"{output_dir}/report_{timestamp}.md"
            
            # Construct the Report content
            report_content = f"# 🚀 CEILING SMASHER REPORT - {timestamp}\n\n"
            
            # Add Master Table (Text representation is hard to capture from Rich Table object easily without Console.export_text)
            # For now, let's focus on the High Value AI Analysis which is already strings.
            # Ideally, scanning results should be tabulated in MD.
            
            if args.scan or args.stocks or args.etfs:
                report_content += "## 📊 Master Portfolio Scan\n"
                # Simple markdown table generation from results
                report_content += "| Ticker | Type | Price | Dist 52wH | RVOL | RSI | Score |\n"
                report_content += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
                for r in all_results[:50]: # Top 50
                    dist = f"{r['pct_from_high']:.2f}%"
                    report_content += f"| {r['ticker']} | {r.get('category', 'Stock')} | ${r['price']:.2f} | {dist} | {r['rvol']:.1f}x | {r['rsi']:.0f} | {r['score']} |\n"
                report_content += "\n---\n\n"

            if args.ai:
                report_content += "## 🤖 The Investment Council Analysis\n\n"
                report_content += f"### 1. Concentrated Alpha (Macro/Growth)\n{analysis_alpha}\n\n---\n\n"
                report_content += f"### 2. Deep Value (Contrarian)\n{analysis_value}\n\n---\n\n"
                report_content += f"### 3. Red Team (Risk Veto)\n{analysis_red}\n\n---\n\n"
                report_content += f"### 4. Agent Ideas from Google (Wealth Multiplier)\n{analysis_google}\n\n---\n\n"
                report_content += f"### 5. Agent Ideas from X (X Intelligence)\n{analysis_x}\n\n---\n\n"
                report_content += f"### 🦁 EXECUTIVE ORDER (CIO)\n{analysis_cio}\n\n"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(report_content)
                
            console.print(f"\n[bold green]✅ Report saved to: {filename}[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]❌ Failed to save report: {e}[/bold red]")

if __name__ == "__main__":
    main()
