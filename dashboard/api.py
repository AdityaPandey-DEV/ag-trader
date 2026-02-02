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
    "logs": ["[SYSTEM] Dashboard started. Waiting for Engine..."],
    "paper_mode": True,
    "initial_capital": 100000.0
}

# Global engine reference for the killswitch endpoint
engine_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine_instance
    # Startup: Initialize and start the engine
    print("[API] Starting background Trading Engine...")
    engine_instance = TradingEngine()
    
    def sync_update(current_symbol="MULTI"):
        state = {
            "regime": get_regime(engine_instance.tsd_count),
            "tsd_count": engine_instance.tsd_count,
            "risk_consumed": engine_instance.risk_manager.daily_pnl,
            "max_drawdown": config.MAX_SESSION_DRAWDOWN_PCT,
            "kill_switch": engine_instance.kill_switch,
            "pnl": round(engine_instance.session_pnl, 2),
            "current_symbol": current_symbol,
            "watchlist": engine_instance.watchlist,
            "positions": engine_instance.broker.get_positions(),
            "planned_trades": engine_instance.planned_trades,
            "logs": engine_instance.logs,
            "paper_mode": engine_instance.paper_mode,
            "initial_capital": engine_instance.initial_capital
        }
        trading_state.update(state)
    
    engine_instance.on_update = sync_update
    thread = threading.Thread(target=engine_instance.start, daemon=True)
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
async def toggle_killswitch():
    if engine_instance:
        engine_instance.kill_switch = not engine_instance.kill_switch
        engine_instance.update_dashboard()
        status = "STOPPED" if engine_instance.kill_switch else "ARMED"
        return {"status": status}
    return {"status": "error"}

@app.post("/toggle_paper")
async def toggle_paper(data: dict):
    if engine_instance:
        enabled = data.get("enabled", True)
        engine_instance.toggle_paper_mode(enabled)
        return {"status": "success", "paper_mode": engine_instance.paper_mode}
    return {"status": "error"}

@app.post("/set_capital")
async def set_capital(data: dict):
    if engine_instance:
        amount = data.get("amount", 100000.0)
        engine_instance.set_initial_capital(float(amount))
        return {"status": "success", "capital": engine_instance.initial_capital}
    return {"status": "error"}

@app.get("/state")
async def get_current_state():
    return {"status": "success", "kill_switch": trading_state.get("kill_switch", False)}

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
