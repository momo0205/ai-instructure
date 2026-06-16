import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from core.engine import GridEngine
from data.db import DailyStat, Trade, Grid, GridStatus as DBGridStatus

logger = logging.getLogger(__name__)

api_app = FastAPI(title="GridBot Dashboard")
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.cache = None

_latest_ai_recommendations: list = []


class DashboardAPI:
    def __init__(self, engine: GridEngine, db_engine, exchange=None):
        self.grid_engine = engine
        self.db_engine = db_engine
        self.exchange = exchange
        self._setup_routes()

    def set_ai_recommendations(self, recs: list):
        global _latest_ai_recommendations
        _latest_ai_recommendations = recs

    def _setup_routes(self):
        ge = self.grid_engine
        dbe = self.db_engine
        ex = self.exchange

        @api_app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            summaries = ge.get_all_summaries()
            total_pnl = ge.get_total_pnl()
            active = ge.get_active_count()
            total_grids = len(summaries)

            balances = {}
            if ex:
                try:
                    raw = ex.fetch_balance()
                    for c in ["USDT", "BTC", "ETH", "SOL"]:
                        free = raw.get(c, {}).get("free", 0) or 0
                        if free > 0:
                            balances[c] = round(free, 6)
                except Exception:
                    balances["USDT"] = 0

            with Session(dbe) as session:
                today = datetime.now().strftime("%Y-%m-%d")
                stat = session.exec(
                    select(DailyStat).where(DailyStat.date == today)
                ).first()

                recent_trades = session.exec(
                    select(Trade).order_by(Trade.sell_filled_at.desc()).limit(20)
                ).all()

                whitelist = []
                running_symbols = {
                    g.symbol
                    for g in session.exec(
                        select(Grid).where(
                            Grid.status.in_([DBGridStatus.RUNNING.value, DBGridStatus.PAUSED.value])
                        )
                    ).all()
                }
                from config.settings import settings
                for sym in settings.COIN_WHITELIST:
                    whitelist.append({
                        "symbol": sym,
                        "in_use": sym in running_symbols,
                    })

            return templates.TemplateResponse(
                request,
                "index.html",
                {
                    "request": request,
                    "summaries": summaries,
                    "total_pnl": round(total_pnl, 4),
                    "active": active,
                    "total_grids": total_grids,
                    "daily_stat": stat,
                    "recent_trades": recent_trades,
                    "balances": balances,
                    "whitelist": whitelist,
                    "ai_recommendations": _latest_ai_recommendations,
                },
            )

        @api_app.get("/grid/{grid_id}", response_class=HTMLResponse)
        async def grid_detail(request: Request, grid_id: int):
            summary = ge.get_summary(grid_id)
            if not summary:
                raise HTTPException(status_code=404, detail="Grid not found")

            with Session(dbe) as session:
                trades = session.exec(
                    select(Trade)
                    .where(Trade.grid_id == grid_id)
                    .order_by(Trade.sell_filled_at.desc())
                    .limit(50)
                ).all()

            return templates.TemplateResponse(
                request,
                "grid_detail.html",
                {
                    "request": request,
                    "summary": summary,
                    "trades": trades,
                },
            )

        @api_app.post("/api/grid/create")
        async def api_create_grid(
            symbol: str = Form(...),
            upper: float = Form(...),
            lower: float = Form(...),
            grid_count: int = Form(20),
            investment: float = Form(...),
            grid_type: str = Form("arithmetic"),
            auto_start: bool = Form(False),
        ):
            grid_id = ge.create_grid(symbol, upper, lower, grid_count, investment, grid_type)
            if grid_id is None:
                raise HTTPException(status_code=400, detail="Risk check failed")
            if auto_start:
                ok = ge.start_grid(grid_id)
                if not ok:
                    raise HTTPException(status_code=500, detail="Grid created but failed to start")
                return {"grid_id": grid_id, "status": "started"}
            return {"grid_id": grid_id, "status": "created"}

        @api_app.post("/api/grid/{grid_id}/start")
        async def api_start_grid(grid_id: int):
            ok = ge.start_grid(grid_id)
            if not ok:
                raise HTTPException(status_code=400, detail="Failed to start grid")
            return {"status": "started"}

        @api_app.post("/api/grid/{grid_id}/pause")
        async def api_pause_grid(grid_id: int):
            ok = ge.pause_grid(grid_id)
            if not ok:
                raise HTTPException(status_code=400, detail="Failed to pause grid")
            return {"status": "paused"}

        @api_app.post("/api/grid/{grid_id}/stop")
        async def api_stop_grid(grid_id: int):
            ok = ge.stop_grid(grid_id)
            if not ok:
                raise HTTPException(status_code=400, detail="Failed to stop grid")
            return {"status": "stopped"}

        @api_app.get("/api/summaries")
        async def api_summaries():
            return ge.get_all_summaries()

        @api_app.get("/api/balance")
        async def api_balance():
            if not ex:
                return JSONResponse({"error": "Exchange not connected"}, status_code=503)
            try:
                raw = ex.fetch_balance()
                result = {}
                for c in ["USDT", "BTC", "ETH", "SOL", "BNB", "XRP"]:
                    free = raw.get(c, {}).get("free", 0) or 0
                    used = raw.get(c, {}).get("used", 0) or 0
                    total = raw.get(c, {}).get("total", 0) or 0
                    if total > 0:
                        result[c] = {"free": round(free, 6), "used": round(used, 6), "total": round(total, 6)}
                return result
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @api_app.get("/api/suggest-interval")
        async def api_suggest_interval(symbol: str, buffer_pct: float = 5.0, grid_count: int = 20):
            if not ex:
                return JSONResponse({"error": "Exchange not connected"}, status_code=503)
            try:
                ticker = ex.fetch_ticker(symbol)
                price = ticker["last"]
                upper = ex.round_price(symbol, price * (1 + buffer_pct / 100))
                lower = ex.round_price(symbol, price * (1 - buffer_pct / 100))
                step = ex.round_price(symbol, (upper - lower) / (grid_count - 1))
                return {
                    "symbol": symbol,
                    "current_price": price,
                    "suggested_upper": upper,
                    "suggested_lower": lower,
                    "grid_count": grid_count,
                    "step": step,
                    "buffer_pct": buffer_pct,
                }
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @api_app.get("/health")
        async def health():
            try:
                exchange_ok = ex is not None and ex.connected

                db_ok = False
                try:
                    with Session(dbe) as s:
                        s.exec(select(DailyStat).limit(1)).first()
                    db_ok = True
                except Exception:
                    pass

                return JSONResponse({
                    "status": "ok" if db_ok else "degraded",
                    "exchange": "connected" if exchange_ok else "disconnected",
                    "database": "ok" if db_ok else "error",
                    "active_grids": ge.get_active_count(),
                    "total_pnl": round(ge.get_total_pnl(), 4),
                })
            except Exception as e:
                return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

        @api_app.post("/api/circuit-breaker/pause-all")
        async def circuit_breaker_pause():
            ge.pause_all()
            return {"status": "paused_all", "message": "All grids paused by circuit breaker"}
