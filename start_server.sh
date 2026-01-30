#!/bin/bash
source venv/bin/activate
echo "🦅 Starting Ceiling Smasher AI Server..."
echo "👉 Open http://localhost:8000 in your browser"
uvicorn web.server:app --reload
