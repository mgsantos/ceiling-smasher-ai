import warnings
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.table import Table
from google import genai
import os
import datetime
import json
import time
from utils.logger import logger
import random

def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def analyze_ideas_from_x(table: Table = None) -> str:
    """
    Persona: Agent Ideas from X (Concentrated Alpha via X.AI)
    Search X platform for high-conviction ideas. 
    Independent execution (does not use table data).
    """
    from openai import OpenAI
    
    xai_key = os.environ.get("XAI_API_KEY")
    if not xai_key:
        return "[red]Error: XAI_API_KEY not found.[/red]"

    client = OpenAI(
        api_key=xai_key,
        base_url="https://api.x.ai/v1"
    )

    try:
        # Load prompt. Independent agent.
        prompt = _load_prompt("agent_ideas_from_X.txt")
        logger.info("Agent 5 (Ideas from X) Started.")
        
        # Log payload for UI/File
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": "grok-3",
            "request": {"contents": "Find me the best concentrated alpha plays for 2026..."},
            "status": "PENDING"
        }
        
        start_t = time.time()
        
        completion = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Find me the best concentrated alpha plays for 2026. Use X Search to validate theses."}
            ],
        )
        
        duration = time.time() - start_t
        result_text = completion.choices[0].message.content
        
        log_entry["status"] = "200 OK"
        log_entry["latency_ms"] = int(duration * 1000)
        log_entry["response"] = {"text": result_text[:200] + "..."}
        
        print(f"__API_LOG__{json.dumps(log_entry)}")
        logger.info(f"Agent 5 (Ideas from X) Finished. Latency: {log_entry['latency_ms']}ms")
        return result_text
        
    except Exception as e:
        logger.error(f"Agent Ideas From X Failed: {e}")
        return f"[red]Agent Ideas From X Failed: {e}[/red]"

def _capture_table(table: Table) -> str:
    console = Console()
    with console.capture() as capture:
        console.print(table)
    return capture.get()

import time
import random

def _generate_with_log(client, model: str, contents: str, config: dict = None) -> str:
    """
    Wrapper to call Gemini API with logging and exponential backoff retry for 429 errors.
    """
    if config is None: config = {}
    
    # payload capture
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": model,
        "request": {
            "contents": contents[:500] + "..." if len(str(contents)) > 500 else contents, 
            "config": config
        },
        "status": "PENDING"
    }
    
    max_retries = 3
    base_delay = 2
    
    start_time = time.time()
    
    # Log start
    logger.info(f"API Request ({model}): {log_entry['request']['contents'][:100]}...")
    
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            duration = time.time() - start_time
            log_entry["status"] = "200 OK"
            log_entry["latency_ms"] = int(duration * 1000)
            log_entry["response"] = {
                "text": response.text[:200] + "..." if response.text else "No Text",
                "usage": response.usage_metadata.model_dump() if response.usage_metadata else {}
            }
            
            # Print special log line for UI
            print(f"__API_LOG__{json.dumps(log_entry)}")
            # Log to file
            logger.info(f"API Response ({model}) [200 OK] {int(duration*1000)}ms: {log_entry['response']['text']}")
            return response.text

        except Exception as e:
            # Check for 429 Resource Exhausted
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries:
                    # Exponential Backoff + Jitter
                    delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    print(f"[yellow]Rate limit hit. Retrying in {delay:.2f}s (Attempt {attempt+1}/{max_retries})...[/yellow]")
                    logger.warning(f"API Rate Limit ({model}). Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    continue
            
            # If not 429 or max retries reached, fail
            duration = time.time() - start_time
            log_entry["status"] = "ERROR"
            log_entry["error"] = error_str
            log_entry["latency_ms"] = int(duration * 1000)
            print(f"__API_LOG__{json.dumps(log_entry)}")
            logger.error(f"API Error ({model}): {error_str}")
            raise e
            
    return "" # Should not reach here

def _load_prompt(filename: str, **kwargs) -> str:
    """
    Loads a prompt from ai/agents/{filename}, and formats it with **kwargs.
    """
    path = os.path.join("ai", "agents", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            template = f.read()
        return template.format(**kwargs)
    except Exception as e:
        # Fallback logging?
        print(f"[red]Error loading prompt {filename}: {e}[/red]")
        # Rethrow or return empty strings?
        # Let's clean the args to debug or just raise
        raise e

def analyze_concentrated_alpha(report_content: str) -> str:
    """
    Persona 1: Concentrated Alpha (Growth/Macro/Kelly)
    Consumes the Fundamentals Report (Growth Section) and Alpha Toolkit Data.
    """
    client = _get_client()
    if not client: return "[red]Error: GEMINI_API_KEY not found.[/red]"
    
    try:
        # Prompt now expects 'report_content' not 'table_str'
        prompt = _load_prompt("agent1_alpha.txt", report_content=report_content)
    except Exception as e:
        return f"[red]Prompt Load Error: {e}[/red]"
    try:
        return _generate_with_log(
            client=client,
            model='gemini-2.0-flash', 
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )
    except Exception as e:
        return f"[red]AI Analysis Failed: {e}[/red]"

def analyze_deep_value(report_content: str) -> str:
    """
    Persona 2: Deep Value (Contrarian/Capital Cycle)
    Consumes the Fundamentals Report (Value Section).
    """
    client = _get_client()
    if not client: return "[red]Error: GEMINI_API_KEY not found.[/red]"
    
    try:
        prompt = _load_prompt("agent2_value.txt", report_content=report_content)
    except Exception as e:
        return f"[red]Prompt Load Error: {e}[/red]"
    try:
        return _generate_with_log(
            client=client,
            model='gemini-2.0-flash', 
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )
    except Exception as e:
        return f"[red]AI Analysis Failed: {e}[/red]"

def extract_tickers_from_analysis(text: str) -> list[str]:
    """
    Helper to extract tickers from the analyst text.
    Robust regex to handle various model formatting quirks.
    """
    import re
    tickers = []
    
    # Pattern 1: "**1. [AAPL]**" or "**1. AAPL**" or "1. [AAPL]"
    # Matches: Number + dot + optional space + optional brackets + TICKER + optional brackets
    # We look for lines starting with a number item
    
    # Find all lines that look like list items for tickers
    # This matches "1. [AAPL]", "**1. AAPL**", "1. AAPL", etc.
    # Group 4 is usually the ticker if we make the prefix flexible
    
    # Simple approach: Find distinct patterns
    
    # 1. Standard "1. [ABCD]" or "1. ABCD" or "**1. [ABCD]**"
    # Matches: Newline -> Optional Markdown (* or _) -> Optional Parens -> Digits -> Dot -> Optional Parens 
    #          -> Optional Markdown -> Optional Brackets -> TICKER -> Optional Brackets
    # Fixed to allow multiple asterisks (e.g. **1.)
    matches_standard = re.findall(r"(?:^|\n)[\*_]*\(?\d+\.\)?\s*[\*_]*\[?([A-Z]{2,6})\]?", text)
    tickers.extend(matches_standard)
    
    # 2. "THE LONG: [ABCD]" or "THE LONG: ABCD" or "THE MOONSHOT: [ABCD]"
    # Removed IGNORECASE to avoid matching "to" or other lowercase words as tickers
    matches_long = re.findall(r"THE (?:LONG|MOONSHOT):?\s*\*?\[?([A-Z]{2,6})\]?\*?", text)
    tickers.extend(matches_long)

    # 3. Grok/General Markdown Headers: "### $TICKER" or "**$TICKER**" or "- $TICKER"
    # Matches: $ + TICKER
    matches_cash = re.findall(r"\$([A-Z]{2,6})", text)
    tickers.extend(matches_cash)
    
    from utils.logger import logger

    clean_tickers = []
    for t in tickers:
        t = t.strip()
        # Filter out common false positives and short words
        if t and len(t) >= 2 and t.upper() not in ["THE", "RSI", "USD", "INPUT", "DATA", "AI", "URL", "PDF", "LONG", "SHORT", "TO", "AND", "OR", "IF"]:
            clean_tickers.append(t.upper())
            
    return list(set(clean_tickers))

def analyze_red_team(tickers: list[str]) -> str:
    """
    Persona 4: The Red Team (Live Research/Fact Checker) - FAST MODE
    Uses Gemini 2.0 Flash with Google Search to autonomously vet tickers.
    """
    client = _get_client()
    if not client: return "[red]Error: GEMINI_API_KEY not found.[/red]"
    
    if not tickers:
        return "No tickers provided to vet."
    
    final_report = "### 🚩 RED TEAM DEEP DIVE REPORT\n\n"

    for ticker in tickers:
        # Console output for UI
        print(f"[bold red]Red Team Vetting: {ticker}...[/bold red]")
        # Log entry
        logger.info(f"Red Team Vetting Started: {ticker}")
        
        final_report += f"#### Analysis: {ticker}\n"

        try:
            # Load prompt asking for specific checks
            prompt_template = _load_prompt("agent4_redteam.txt", ticker_str=ticker)
            
            # Augment prompt to force search tool usage
            prompt = (
                f"{prompt_template}\n\n"
                f"COMMAND: You have access to Google Search. You MUST use it to search for the following regarding {ticker}:\n"
                f"1. Recent lawsuits or fraud allegations.\n"
                f"2. Aggressive insider selling in the last 6 months.\n"
                f"3. Short seller reports or accounting irregularities.\n"
                f"4. Major regulatory risks.\n\n"
                f"Synthesize your findings. If you find VERIFIED red flags, VETO the stock. If it's pure noise or clean, APPROVE it. Be harsh and concise."
            )

            # Call Gemini 2.0 Flash with Search Tool
            analysis = _generate_with_log(
                client=client, 
                model='gemini-2.0-flash', 
                contents=prompt,
                config={'tools': [{'google_search': {}}]}
            )
            
            final_report += f"{analysis}\n\n---\n"
            
        except Exception as e:
            logger.error(f"Red Team Vetting Failed for {ticker}: {e}")
            final_report += f"Error analyzing {ticker}: {e}\n\n"
            
    return final_report

def analyze_ideas_from_google(table: Table = None) -> str:
    """
    Persona: Agent Ideas from Google (Wealth Multiplier)
    Focuses on high-risk/high-reward 'Life Changing' plays via Google Search.
    Independent execution.
    """
    client = _get_client()
    if not client: return "[red]Error: GEMINI_API_KEY not found.[/red]"
    
    # Independent agent, table not strictly needed by new prompt architecture
    # but kept as optional arg for compatibility if restored.
    # table_str = _capture_table(table) 

    try:
        # Load prompt without table_str as per new user request for independence
        prompt = _load_prompt("agent_ideas_from_Google.txt")
    except Exception as e:
        return f"[red]Prompt Load Error: {e}[/red]"
    
    try:
        # Enable Google Search for fresh news verification if needed (optional for CIO but good for final checks)
        return _generate_with_log(
            client=client,
            model='gemini-2.0-flash', 
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )
    except Exception as e:
        return f"[red]Agent Ideas From Google Failed: {e}[/red]"

def analyze_alpha_toolkit() -> str:
    """
    Persona: Director of Asymmetric Information (Alpha Toolkit)
    Compiles "Whale Tracks", "Capitol Trades", and "Insider Buying" from the web.
    """
    client = _get_client()
    if not client: return "[red]Error: GEMINI_API_KEY not found.[/red]"
    
    # 1. Define the search queries for "Asymmetric Data"
    # We want fresh data.
    current_year = datetime.datetime.now().year
    queries = [
        f"WhaleWisdom top hedge fund buys {current_year} Q{((datetime.datetime.now().month-1)//3)+1}", # Current Quarter 13Fs
        "Quiver Quantitative congress trading stock anomalies this month",
        "OpenInsider top CEO buying last 30 days significant",
        "Koyfin macro market anomalies current month analysis"
    ]
    
    print("[bold cyan]🕵️  Hunting for Asymmetric Information (Whales, Congress, Insiders)...[/bold cyan]")
    
    search_results_text = ""
    
    # 2. Iterate and Search (using Gemini with Google Search tool for better synthesis, 
    # but let's stick to the pattern of 'search -> synthesize' or 'use tool directly')
    
    # Let's use the tool-use capability of Gemini 2.0 Flash for this, 
    # as it's better at browsing multiple topics.
    
    try:
        prompt = _load_prompt("agent_alpha_toolkit.txt", search_results="[SYSTEM: The AI will fetch these results directly via Google Search tool]")
        
        # We append a specific instruction to force the tool use across these domains
        prompt += f"\n\nCOMMAND: Use your Google Search tool to find the LATEST info on:\n"
        for q in queries:
            prompt += f"- {q}\n"
        prompt += "\nSynthesize the findings into the requested format."

        return _generate_with_log(
            client=client,
            model='gemini-2.0-flash', 
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )
        
    except Exception as e:
        logger.error(f"Alpha Toolkit Analysis Failed: {e}")
        return f"[red]Alpha Toolkit Analysis Failed: {e}[/red]"


def execute_portfolio_strategy(report_content: str, agent1_analysis: str, agent2_analysis: str, red_team_analysis: str, analysis_google: str, analysis_x: str = "", **kwargs) -> str:
    """
    Persona 3: The Portfolio Manager (The Boss) - CIO
    Synthesizes inputs from the Growth and Value analysts + Red Team Intel + Google & X Agents to create final execution orders.
    """
    client = _get_client()
    if not client: return "[red]Error: GEMINI_API_KEY not found.[/red]"
    
    try:
        # PRE-FILTER CONTEXT for "Lost in the Middle" prevention
        # The report_content can be massive (thousands of lines). We only want the "HITs".
        clean_report_content = "### PRE-FILTERED DATA HIGHLIGHTS\n\n"
        
        # Simple string processing to keep relevant lines
        # We look for lines containing "HIT", "MATCH", "Score", or Table Headers with pipes
        for line in report_content.splitlines():
            if "HIT" in line or "MATCH" in line or "Score" in line or "|" in line or "#" in line:
                 clean_report_content += line + "\n"
        
        # Fallback if filter was too aggressive
        if len(clean_report_content) < 500:
             clean_report_content = report_content[:20000] # Just take the first 20k chars

        try:
            prompt = _load_prompt("agent3_cio.txt", 
                                  report_content=clean_report_content, 
                                  agent1_analysis=agent1_analysis, 
                                  agent2_analysis=agent2_analysis, 
                                  red_team_analysis=red_team_analysis, 
                                  analysis_google=analysis_google,
                                  analysis_x=analysis_x,
                                  alpha_toolkit_data=kwargs.get('alpha_toolkit_data', 'No asymmetric data available.'))
        except Exception as e:
            return f"[red]Prompt Load Error: {e}[/red]"
        
        return _generate_with_log(
            client=client,
            model='gemini-2.0-flash',  # Keeping Flash for speed, but Context is now cleaner. 
            # If user has access, 'gemini-1.5-pro' would be better here.
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )
    except Exception as e:
        return f"[red]AI Analysis Failed: {e}[/red]"

def execute_portfolio_manager(portfolio: list, cio_analysis: str, **kwargs) -> str:
    """
    Persona 6: The Portfolio Manager (The Executioner)
    Reconciles CIO strategy with Live Portfolio (IBKR) to issue concrete orders.
    """
    client = _get_client()
    if not client: return "[red]Error: GEMINI_API_KEY not found.[/red]"

    # Format Portfolio for LLM
    if not portfolio:
        portfolio_str = "No current positions (Cash only)."
    else:
        portfolio_str = "CURRENT HOLDINGS:\n"
        for p in portfolio:
            # Include Description (Company Name) to prevent hallucinations
            desc = p.get('description', '')
            portfolio_str += f"- {p.get('ticker')} ({desc}) [{p.get('secType')}]: {p.get('position')} units @ avg cost ${p.get('avg_cost', 0):.2f}\n"

    try:
        alpha_data = kwargs.get('alpha_toolkit_data', 'No asymmetric data available.')
        prompt = _load_prompt("agent_pm.txt", portfolio_str=portfolio_str, cio_analysis=cio_analysis, alpha_toolkit_data=alpha_data)
    except Exception as e:
        return f"[red]Prompt Load Error: {e}[/red]"
    
    try:
        # Enable Google Search for Fact Checking
        return _generate_with_log(
            client=client,
            model='gemini-2.5-pro', 
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )
    except Exception as e:
        return f"[red]PM Execution Failed: {e}[/red]"

def execute_portfolio_manager_grok(portfolio: list, cio_analysis: str, **kwargs) -> str:
    """
    Persona 6b: The Portfolio Manager (The Executioner) - GROK EDITION
    Reconciles CIO strategy with Live Portfolio using X.AI (Grok).
    """
    from openai import OpenAI
    
    xai_key = os.environ.get("XAI_API_KEY")
    if not xai_key:
        return "[red]Error: XAI_API_KEY not found.[/red]"

    client = OpenAI(
        api_key=xai_key,
        base_url="https://api.x.ai/v1"
    )

    # Format Portfolio for LLM
    if not portfolio:
        portfolio_str = "No current positions (Cash only)."
    else:
        portfolio_str = "CURRENT HOLDINGS:\n"
        for p in portfolio:
            # Include Description (Company Name) to prevent hallucinations
            desc = p.get('description', '')
            portfolio_str += f"- {p.get('ticker')} ({desc}) [{p.get('secType')}]: {p.get('position')} units @ avg cost ${p.get('avg_cost', 0):.2f}\n"

    try:
        # Re-use the same prompt template (agent_pm.txt)
        alpha_data = kwargs.get('alpha_toolkit_data', 'No asymmetric data available.')
        prompt = _load_prompt("agent_pm.txt", portfolio_str=portfolio_str, cio_analysis=cio_analysis, alpha_toolkit_data=alpha_data)
    except Exception as e:
        return f"[red]Prompt Load Error: {e}[/red]"
    
    try:
        logger.info("PM Agent (Grok) Started.")
        start_t = time.time()
        
        # Log payload
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": "grok-3",
            "request": {"contents": "Review the portfolio and issue execution orders..."},
            "status": "PENDING"
        }

        completion = client.chat.completions.create(
            model="grok-3", # Fixed: grok-2 -> grok-3 (User confirmed working model from Agent X)
            # Using prompt as system message for strong adherence
            messages=[
                {"role": "system", "content": prompt},
                {"role": "system", "content": "CRITICAL: You have access to real-time information. You MUST use your search/browsing capabilities to validating the business models of these tickers before declaring them redundant. Do not hallucinate."},
                {"role": "user", "content": "Review the portfolio and issue execution orders. Verify correlations with live data."}
            ],
            temperature=0.7
        )
        
        duration = time.time() - start_t
        result_text = completion.choices[0].message.content
        
        log_entry["status"] = "200 OK"
        log_entry["latency_ms"] = int(duration * 1000)
        log_entry["response"] = {"text": result_text[:200] + "..."}
        
        print(f"__API_LOG__{json.dumps(log_entry)}")
        logger.info(f"PM Agent (Grok) Finished. Latency: {log_entry['latency_ms']}ms")
        
        return result_text
        
    except Exception as e:
        logger.error(f"PM Execution (Grok) Failed: {e}")
        return f"[red]PM Execution (Grok) Failed: {e}[/red]"
