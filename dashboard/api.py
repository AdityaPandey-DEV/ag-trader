from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import threading
import os
import sys
import asyncio
import json
from contextlib import asynccontextmanager

# Ensure project root is in path for cloud deployment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import TradingEngine
from config.settings import config
from core.indicators import get_regime

try:
    from uvicorn.protocols.utils import ClientDisconnected
except ImportError:
    class ClientDisconnected(Exception): pass

# Initial Shared state
trading_state = {
    "regime": "WAITING",
    "tsd_count": 0,
    "risk_consumed": 0.0,
    "max_drawdown": 1.5,
    "kill_switch": False,
    "realized_pnl": 0.0,
    "pnl": 0.0,
    "current_symbol": "NONE",
    "watchlist": [],
    "positions": [],
    "planned_trades": [],
    "equity_history": [{"time": "START", "equity": 100000}],
    "logs": ["[SYSTEM] Dashboard started. Waiting for Engine..."]
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and start the engine
    print("[API] Starting background Trading Engine...")
    engine = TradingEngine()
    
    def sync_update(current_symbol="MULTI"):
        state = {
            "regime": get_regime(engine.tsd_count),
            "tsd_count": engine.tsd_count,
            "risk_consumed": engine.risk_manager.daily_pnl,
            "max_drawdown": config.MAX_SESSION_DRAWDOWN_PCT,
            "kill_switch": False,
            "pnl": round(engine.session_pnl, 2),
            "current_symbol": current_symbol,
            "watchlist": engine.watchlist,
            "positions": engine.broker.positions,
            "planned_trades": engine.planned_trades,
            "logs": engine.logs
        }
        trading_state.update(state)
    
    engine.update_dashboard = sync_update
    thread = threading.Thread(target=engine.start, daemon=True)
    thread.start()
    print("[API] Trading Engine thread launched.")
    yield
    print("[API] Shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def get_status():
    return trading_state

@app.post("/update")
async def update_state(request: Request):
    """Bridge for the TradingEngine to push live data."""
    global trading_state
    new_data = await request.json()
    trading_state.update(new_data)
    return {"status": "success"}

@app.post("/killswitch")
async def toggle_kill_switch():
    trading_state["kill_switch"] = not trading_state["kill_switch"]
    return {"status": "success", "kill_switch": trading_state["kill_switch"]}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            await websocket.send_text(json.dumps(trading_state))
            await asyncio.sleep(1) # Refresh rate
        except (WebSocketDisconnect, ClientDisconnected, RuntimeError):
            break
        except Exception:
            break

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
