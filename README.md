# 🚀 Ceiling Smasher AI Hedge Fund

An autonomous, AI-powered hedge fund system that scans markets, analyzes high-conviction plays using a "Council" of AI agents (Gemini & Grok), and executes trades via Interactive Brokers.

## 🧠 Architecture

The system operates in a multi-stage pipeline:

1.  **Market Scanning (The Eyes)**:
    *   **US Stocks**: Scans S&P 500 & Nasdaq 100 for breakouts and high relative volume (RVOL).
    *   **International**: Scans top ADRs (TSM, ASML, MELI, etc.).
    *   **ETFs**: Scans leverage/macro ETFs (TQQQ, SOXL, NVDL).
2.  **The Investment Council (The Brain)**:
    *   **Agent 1 (Alpha)**: Concentrated bets on macro/growth trends.
    *   **Agent 2 (Value)**: Deep value and contrarian capital cycle analysis.
    *   **Agent 3 (Red Team)**: A "Forensic Accountant" that uses Google Search (SerpAPI) & Jina AI to vet tickers for fraud or risks.
    *   **Agent 4 (CIO)**: Synthesizes all inputs to make the final "Buy" or "Pass" decision.
    *   **Agent 5 (Grok)**: Live X platform intelligence.
3.  **Mission Control (The Interface)**:
    *   A FastApi-based web dashboard (`/static/index.html`) that streams real-time logs and displays findings.
4.  **Execution (The Hands)**:
    *   Connects to Interactive Brokers (IBKR) Gateway to fetch live portfolios and (potentially) execute orders.

## 🛠️ Tech Stack

*   **Core**: Python 3.9+
*   **Web Framework**: FastAPI (Async/Await) + Uvicorn
*   **Real-time**: Server-Sent Events (SSE)
*   **AI Models**:
    *   Google Gemini 2.0 Flash / 2.5 Pro (Reasoning & Tool Use)
    *   xAI Grok 3 Beta (Live Social Sentiment)
*   **Broker**: Interactive Brokers API (`ib_insync`)
*   **Frontend**: TailwindCSS + Marked.js (No build step required)
*   **CLI UI**: Rich

## 📦 Installation

### Prerequisites
*   Python 3.9+
*   Interactive Brokers TWS or IB Gateway installed and running.
    *   Enable "Enable ActiveX and Socket Clients".
    *   Port: `4001` (Gateway) or `7496` (Live TWS) / `7497` (Paper).

### Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/mgsantos/ceiling-smasher-ai.git
    cd ceiling-smasher-ai
    ```

2.  **Create Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**
    Create a `.env` file in the root directory:
    ```ini
    # Models
    GEMINI_API_KEY=your_gemini_key
    XAI_API_KEY=your_grok_key

    # Research
    SERPAPI_API_KEY=your_serpapi_key

    # Broker (Optional defaults)
    IB_HOST=127.0.0.1
    IB_PORT=4001
    IB_CLIENT_ID=6
    ```

## 🚀 Usage

### 1. Mission Control (Web UI)
The recommended way to run the system.

```bash
# Start the server
./start_server.sh
```
*   Open [http://localhost:8000/static/index.html](http://127.0.0.1:8000/static/index.html).
*   Use the **"Invoke Council"** button to trigger a full run.
*   View live logs and historical reports in the sidebar.

### 2. CLI Mode (Manual)
You can run individual modules directly from the terminal.

```bash
# Full Market Scan + AI Analysis
python main.py --scan --full --ai --save-report

# Just Fetch Live Portfolio
python main.py --portfolio

# Just Asymmetric Intel (Whale Tracks)
python main.py --alpha-toolkit
```

## 📂 Project Structure

*   `main.py`: Entry point and orchestrator.
*   `web/`: User Interface and API server.
*   `ai/`: AI Analyst definitions (Agents).
*   `stocks_us/`, `etfs/`: Market scanning logic.
*   `broker/`: IBKR connection handler.
*   `output/`: Generated Markdown reports.
