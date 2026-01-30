import os
import subprocess
import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import glob
import time
from ai import analyst as ai_analyst
from broker import ibkr
from utils.logger import logger

app = FastAPI()

# Ensure output directory exists
OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Mount static files (Frontend)
app.mount("/static", StaticFiles(directory="web/static"), name="static")

class RunRequest(BaseModel):
    command_args: list[str] = []

async def run_analysis_generator():
    """
    Generator that runs the analysis command and yields stdout lines as SSE events.
    Uses asyncio.subprocess for non-blocking I/O.
    """
    cmd = "python -u main.py --scan --full --ai --save-report"
    
    # Run process asynchronously
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    yield {"event": "start", "data": "🚀 Starting Analysis Process..."}
    
    try:
        # Stream stdout line by line asynchronously
        async for line in process.stdout:
            decoded_line = line.decode('utf-8')
            if decoded_line:
                if "__API_LOG__" in decoded_line:
                    try:
                        clean_line = decoded_line.strip().replace("__API_LOG__", "")
                        yield {"event": "api_log", "data": clean_line}
                    except:
                        yield {"event": "log", "data": decoded_line}
                else:
                    yield {"event": "log", "data": decoded_line}
                    
        # Wait for completion
        return_code = await process.wait()
        
        if return_code == 0:
            yield {"event": "complete", "data": "✅ Analysis Complete."}
            # Provide the latest file
            files = glob.glob(f"{OUTPUT_DIR}/*.md")
            if files:
                latest_file = max(files, key=os.path.getctime)
                yield {"event": "file_created", "data": os.path.basename(latest_file)}
        else:
            stderr_bytes = await process.stderr.read()
            stderr = stderr_bytes.decode('utf-8')
            yield {"event": "error", "data": f"Process failed with code {return_code}: {stderr}"}
            
    except Exception as e:
        yield {"event": "error", "data": f"Server Error: {str(e)}"}
        if process.returncode is None:
             try: process.kill()
             except: pass

async def run_portfolio_generator():
    """
    Generator that runs the portfolio command and yields stdout lines as SSE events.
    """
    cmd = "python -u main.py --portfolio"
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    yield {"event": "start", "data": "💼 Fetching Live Portfolio..."}

    try:
        async for line in process.stdout:
            decoded_line = line.decode('utf-8')
            if decoded_line:
                yield {"event": "log", "data": decoded_line}
                
        return_code = await process.wait()
        
        if return_code == 0:
            yield {"event": "complete", "data": "✅ Portfolio Fetch Complete."}
        else:
            stderr_bytes = await process.stderr.read()
            stderr = stderr_bytes.decode('utf-8')
            yield {"event": "error", "data": f"Process failed with code {return_code}: {stderr}"}
            
    except Exception as e:
        yield {"event": "error", "data": f"Server Error: {str(e)}"}
        if process.returncode is None:
             try: process.kill() 
             except: pass

@app.get("/api/stream-run")
async def stream_run():
    """
    Endpoint for EventSource to connect and trigger the main analysis.
    """
    logger.info("UI Action: Invoke Investment Council triggered.")
    return EventSourceResponse(run_analysis_generator())

@app.get("/api/stream-portfolio")
async def stream_portfolio():
    """
    Endpoint for EventSource to connect and trigger portfolio fetch.
    """
    logger.info("UI Action: Fetch Portfolio triggered.")
    return EventSourceResponse(run_portfolio_generator())

async def run_alpha_toolkit_generator():
    """
    Generator that runs the alpha toolkit command and yields stdout lines as SSE events.
    """
    cmd = "python -u main.py --alpha-toolkit"
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    yield {"event": "start", "data": "🕵️ Fetching Asymmetric Information (Alpha Toolkit)..."}

    try:
        async for line in process.stdout:
            decoded_line = line.decode('utf-8')
            if decoded_line:
                if "__API_LOG__" in decoded_line:
                    try:
                        clean_line = decoded_line.strip().replace("__API_LOG__", "")
                        yield {"event": "api_log", "data": clean_line}
                    except:
                        yield {"event": "log", "data": decoded_line}
                else:
                    yield {"event": "log", "data": decoded_line}
                
        return_code = await process.wait()
        
        if return_code == 0:
            yield {"event": "complete", "data": "✅ Alpha Toolkit Report Generated."}
            files = glob.glob(f"{OUTPUT_DIR}/alpha_toolkit_*.md")
            if files:
                latest_file = max(files, key=os.path.getctime)
                yield {"event": "file_created", "data": os.path.basename(latest_file)}
        else:
            stderr_bytes = await process.stderr.read()
            stderr = stderr_bytes.decode('utf-8')
            yield {"event": "error", "data": f"Process failed with code {return_code}: {stderr}"}
            
    except Exception as e:
        yield {"event": "error", "data": f"Server Error: {str(e)}"}
        if process.returncode is None:
             try: process.kill()
             except: pass

@app.get("/api/stream-alpha-toolkit")
async def stream_alpha_toolkit():
    """
    Endpoint for EventSource to connect and trigger alpha toolkit fetch.
    """
    logger.info("UI Action: Fetch Alpha Toolkit triggered.")
    return EventSourceResponse(run_alpha_toolkit_generator())

async def run_pm_review_generator(filename: str, model: str = "gemini"):
    """
    Generator that runs the PM Review command and yields stdout lines as SSE events.
    """
    report_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(report_path):
        yield {"event": "error", "data": f"Report file not found: {filename}"}
        return

    cmd = f"python -u main.py --review-report {report_path} --pm-model {model}"
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    yield {"event": "start", "data": f"🦁 Running Portfolio Manager ({model.upper()}) on {filename}..."}

    try:
        async for line in process.stdout:
            decoded_line = line.decode('utf-8')
            if decoded_line:
                if "__API_LOG__" in decoded_line:
                    try:
                        clean_line = decoded_line.strip().replace("__API_LOG__", "")
                        yield {"event": "api_log", "data": clean_line}
                    except:
                        yield {"event": "log", "data": decoded_line}
                else:
                    yield {"event": "log", "data": decoded_line}
                
        return_code = await process.wait()
        
        if return_code == 0:
            yield {"event": "complete", "data": f"✅ PM Execution ({model.upper()}) Complete."}
        else:
            stderr_bytes = await process.stderr.read()
            stderr = stderr_bytes.decode('utf-8')
            yield {"event": "error", "data": f"Process failed with code {return_code}: {stderr}"}
            
    except Exception as e:
        yield {"event": "error", "data": f"Server Error: {str(e)}"}
        if process.returncode is None:
             try: process.kill()
             except: pass

@app.get("/api/stream-pm")
async def stream_pm(report: str, model: str = "gemini"):
    """
    Endpoint for EventSource to connect and trigger PM review.
    """
    logger.info(f"UI Action: Run PM Agent triggered. Report: {report}, Model: {model}")
    return EventSourceResponse(run_pm_review_generator(report, model))

@app.get("/api/reports")
def list_reports():
    files = glob.glob(f"{OUTPUT_DIR}/*.md")
    # Sort key: modification time, descending
    files.sort(key=os.path.getmtime, reverse=True)
    results = []
    for f in files:
        stats = os.stat(f)
        results.append({
            "name": os.path.basename(f),
            "size": stats.st_size,
            "created": stats.st_mtime
        })
    return results

@app.get("/api/reports/{filename}")
async def get_report_content(filename: str):
    # Security check: filename must be strictly alphanumeric + .md + - _ to prevent traversal
    # Simplify: ensure it doesn't contain "/" or "\\"
    if "/" in filename or "\\" in filename:
         raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}

@app.get("/api/status")
async def get_system_status():
    """
    Returns the age (in seconds) of the critical system data files.
    Used to show fresh/stale indicators in the Mission Control.
    """
    status = {
        "report_age": None,
        "alpha_age": None,
        "portfolio_live": False
    }
    
    # 0. Check IBKR Connection
    try:
        status["portfolio_live"] = ibkr.check_connection_status()
    except: pass
    
    # 1. Check Output Reports
    try:
        report_files = glob.glob(os.path.join(OUTPUT_DIR, "report_*.md"))
        if report_files:
            latest = max(report_files, key=os.path.getctime)
            age = time.time() - os.path.getctime(latest)
            status["report_age"] = int(age)
    except: pass
    
    # 2. Check Alpha Toolkit
    try:
        alpha_files = glob.glob(os.path.join(OUTPUT_DIR, "alpha_toolkit_*.md"))
        if alpha_files:
            latest = max(alpha_files, key=os.path.getctime)
            age = time.time() - os.path.getctime(latest)
            status["alpha_age"] = int(age)
    except: pass
    
    return status

@app.get("/")
def read_root():
    return JSONResponse(status_code=200, content={"message": "API Running. Go to /static/index.html"})

# --- Agent Management API ---
AGENTS_DIR = os.path.join("ai", "agents")

class AgentContent(BaseModel):
    content: str

@app.get("/api/agents")
def list_agents():
    files = glob.glob(f"{AGENTS_DIR}/*.txt")
    results = []
    for f in files:
        results.append(os.path.basename(f))
    results.sort()
    return results

@app.get("/api/agents/{filename}")
def get_agent(filename: str):
    path = os.path.join(AGENTS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return JSONResponse(status_code=404, content={"message": "Agent not found"})

@app.post("/api/agents/{filename}")
def save_agent(filename: str, agent: AgentContent):
    path = os.path.join(AGENTS_DIR, filename)
    
    # 1. Create Backup
    if os.path.exists(path):
        backup_path = path + ".bak"
        with open(path, "r", encoding="utf-8") as f_orig:
            with open(backup_path, "w", encoding="utf-8") as f_bak:
                f_bak.write(f_orig.read())
    
    # 2. Save New Content
    with open(path, "w", encoding="utf-8") as f:
        f.write(agent.content)
        
    return {"message": "Saved successfully", "backup": f"{filename}.bak"}
