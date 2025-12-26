"""
Stockman - AI Stock Research Assistant
Main FastAPI Application
"""

import os
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json

# Add backend directory to path for Vercel compatibility
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from memory import MemoryManager
from data_sources.aggregator import DataAggregator
from briefing import BriefingGenerator

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Stockman", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
memory = MemoryManager()
data_aggregator = DataAggregator()
briefing_generator = BriefingGenerator()

# ============== Models ==============

class ChatMessage(BaseModel):
    message: str
    is_voice: bool = False

class StockAction(BaseModel):
    ticker: str
    shares: Optional[float] = None
    price: Optional[float] = None

class SettingsUpdate(BaseModel):
    name: Optional[str] = None
    preferences: Optional[dict] = None

# ============== API Routes ==============

@app.get("/")
async def root():
    """Serve the main app - on Vercel this is handled by static routing"""
    frontend_path = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    if os.path.exists(frontend_path):
        return HTMLResponse(open(frontend_path).read())
    # On Vercel, the frontend is served via static routing
    return {"message": "Stockman API - frontend served separately"}

@app.get("/api/health")
async def health():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ---------- Chat ----------

@app.post("/api/chat")
async def chat(msg: ChatMessage):
    """Main chat endpoint - talk to Stockman"""
    try:
        # Get user context
        context = memory.get_full_context()

        # Get current market data for watchlist
        watchlist = memory.get_watchlist()
        portfolio = memory.get_portfolio()
        tickers = list(set([s['ticker'] for s in watchlist] + [s['ticker'] for s in portfolio]))

        market_data = {}
        if tickers:
            market_data = await data_aggregator.get_stock_data(tickers)

        # Build prompt with context
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        user_name = context.get('profile', {}).get('name', 'Friend')
        system_prompt = f"""You are Stockman - a personal stock research assistant who works exclusively for {user_name}. You're not a generic AI - you're THEIR dedicated assistant who knows their portfolio, preferences, and investment style.

== WHO YOU'RE TALKING TO ==
Name: {user_name}
Their Portfolio: {json.dumps(portfolio, indent=2) if portfolio else "Not set up yet"}
Their Watchlist: {json.dumps(watchlist, indent=2) if watchlist else "Not tracking anything yet"}

== CURRENT MARKET DATA ==
{json.dumps(market_data, indent=2) if market_data else "No stocks being tracked"}

== YOUR MEMORY OF PAST CONVERSATIONS ==
{json.dumps(context.get('recent_messages', [])[-10:], indent=2)}

== HOW TO RESPOND ==
1. Be conversational and direct - talk like a knowledgeable friend, not a formal assistant
2. Give clear, actionable insights - not walls of text
3. When discussing stocks, lead with the key point (up/down, opportunity, concern)
4. Use simple formatting: short paragraphs, bullet points for lists
5. If they own a stock, acknowledge it ("Your AAPL position..." not "AAPL...")
6. Remember what they've told you and reference it naturally
7. Be honest about risks and uncertainties
8. Keep responses focused - 2-4 short paragraphs max unless they ask for detail

== FORMATTING RULES ==
- Use **bold** for emphasis on key numbers or insights
- Use bullet points for lists (- item)
- Keep paragraphs short (2-3 sentences)
- Don't use headers or excessive formatting
- Sound human, not robotic"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": msg.message}]
        )

        assistant_reply = response.content[0].text

        # Save to memory
        memory.add_message("user", msg.message)
        memory.add_message("assistant", assistant_reply)

        return {
            "reply": assistant_reply,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Portfolio Management ----------

@app.get("/api/portfolio")
async def get_portfolio():
    """Get current portfolio"""
    portfolio = memory.get_portfolio()
    return {"portfolio": portfolio}

@app.post("/api/portfolio/add")
async def add_to_portfolio(stock: StockAction):
    """Add stock to portfolio"""
    memory.add_to_portfolio(stock.ticker.upper(), stock.shares, stock.price)
    return {"success": True, "message": f"Added {stock.ticker.upper()} to portfolio"}

@app.delete("/api/portfolio/{ticker}")
async def remove_from_portfolio(ticker: str):
    """Remove stock from portfolio"""
    memory.remove_from_portfolio(ticker.upper())
    return {"success": True, "message": f"Removed {ticker.upper()} from portfolio"}

# ---------- Watchlist Management ----------

@app.get("/api/watchlist")
async def get_watchlist():
    """Get current watchlist"""
    watchlist = memory.get_watchlist()
    return {"watchlist": watchlist}

@app.post("/api/watchlist/add")
async def add_to_watchlist(stock: StockAction):
    """Add stock to watchlist"""
    memory.add_to_watchlist(stock.ticker.upper())
    return {"success": True, "message": f"Added {stock.ticker.upper()} to watchlist"}

@app.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    """Remove stock from watchlist"""
    memory.remove_from_watchlist(ticker.upper())
    return {"success": True, "message": f"Removed {ticker.upper()} from watchlist"}

# ---------- Morning Briefing ----------

@app.get("/api/briefing")
async def get_briefing():
    """Generate morning briefing"""
    try:
        briefing = await briefing_generator.generate_briefing(memory, data_aggregator)
        return briefing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/morning-wisdom")
async def get_morning_wisdom():
    """Get today's wisdom quote for morning notification"""
    quote = briefing_generator.get_daily_quote()
    return {
        "wisdom": quote["quote"],
        "date": datetime.now().strftime("%Y-%m-%d")
    }

# ---------- Stock Data ----------

@app.get("/api/stock/{ticker}")
async def get_stock_info(ticker: str):
    """Get detailed info about a specific stock"""
    try:
        data = await data_aggregator.get_stock_data([ticker.upper()])
        if ticker.upper() in data:
            return data[ticker.upper()]
        raise HTTPException(status_code=404, detail="Stock not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{ticker}/score")
async def get_stock_score(ticker: str):
    """Get opportunity score for a stock"""
    try:
        score = await data_aggregator.calculate_opportunity_score(ticker.upper())
        return score
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Settings ----------

@app.get("/api/settings")
async def get_settings():
    """Get user settings and profile"""
    return memory.get_profile()

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """Update user settings"""
    if settings.name:
        memory.update_profile(name=settings.name)
    if settings.preferences:
        memory.update_preferences(settings.preferences)
    return {"success": True}

# ---------- Voice ----------

@app.post("/api/voice/transcribe")
async def transcribe_audio(request: Request):
    """Transcribe audio using Whisper"""
    try:
        from openai import OpenAI
        import tempfile

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Get audio data from request
        form = await request.form()
        audio_file = form.get("audio")

        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")

        # Read the audio content
        audio_content = await audio_file.read()

        # Save to a temporary file with proper extension
        # OpenAI needs the file extension to determine format
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_content)
            tmp_path = tmp.name

        try:
            # Transcribe with Whisper using the file path
            with open(tmp_path, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )
            return {"text": transcript.text}
        finally:
            # Clean up temp file
            import os as os_module
            os_module.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/synthesize")
async def synthesize_speech(request: Request):
    """Convert text to speech using ElevenLabs"""
    try:
        from elevenlabs import ElevenLabs

        data = await request.json()
        text = data.get("text", "")

        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

        # Use configured voice or default
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel

        audio = client.generate(
            text=text,
            voice=voice_id,
            model="eleven_monolingual_v1"
        )

        # Return audio as bytes
        audio_bytes = b"".join(audio)

        return JSONResponse(
            content={"audio": audio_bytes.hex()},
            media_type="application/json"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files (only for local development - Vercel handles this via routes)
frontend_dir = os.path.join(os.path.dirname(__file__), "../frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
