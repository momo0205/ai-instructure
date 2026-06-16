import logging
import os
import signal
import sys
from datetime import datetime

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from core.exchange import OKXExchange
from core.risk import RiskManager
from core.engine import GridEngine
from ai.sentiment import SentimentAnalyzer
from ai.selector import CoinSelector
from ai.regime import RegimeDetector
from ai.alert import AlertManager
from data.collector import MarketDataCollector
from data.db import DailyStat, init_db


def setup_logging():
    from logging.handlers import RotatingFileHandler

    os.makedirs("data", exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            "data/gridbot.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except Exception:
        pass

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("ccxt").setLevel(logging.WARNING)


def check_config():
    missing = []
    if not settings.OKX_API_KEY:
        missing.append("OKX_API_KEY")
    if not settings.OKX_SECRET:
        missing.append("OKX_SECRET")
    if not settings.OKX_PASSWORD:
        missing.append("OKX_PASSWORD")

    if missing:
        print(f"[WARN] 缺少配置: {', '.join(missing)}")
        if not settings.OKX_SANDBOX:
            print("[WARN] OKX_SANDBOX=False 但 API 密钥未配置，将无法连接交易所")
        else:
            print("[INFO] 沙盒模式下可以创建网格但无法实际交易，请配置 API 密钥")

    if not settings.LLM_API_KEY:
        print("[WARN] LLM_API_KEY 未配置，AI 功能不可用")

    if not settings.OKX_PROXY:
        print("[INFO] OKX_PROXY 未配置，如在大陆网络环境可能无法连接 OKX")
        print("[INFO] 可设置代理: export OKX_PROXY=http://127.0.0.1:7890")

    print(f"[INFO] LLM: {settings.LLM_PROVIDER}/{settings.LLM_MODEL}")
    print(f"[INFO] Sandbox: {settings.OKX_SANDBOX}")
    print(f"[INFO] Whitelist: {settings.COIN_WHITELIST}")


def ai_analysis_job(engine: GridEngine, collector: MarketDataCollector,
                    sentiment: SentimentAnalyzer, selector: CoinSelector,
                    regime: RegimeDetector, db_engine, dashboard=None):
    logger = logging.getLogger("ai_job")
    logger.info("Running AI analysis...")

    try:
        top_coins = collector.get_top_coins_by_volume(limit=30)
        indicators = {}
        for coin in top_coins[:15]:
            try:
                indicators[coin["symbol"]] = collector.calculate_indicators(coin["symbol"])
            except Exception as e:
                logger.warning(f"Failed indicators for {coin['symbol']}: {e}")

        coin_summary = "\n".join(
            f"{c['symbol']}: {c['change_24h']:+.2f}%, vol={c['volume_24h']:.0f}"
            for c in top_coins[:10]
        )
        market_summary = f"Top 10 volume coins analyzed. {len(indicators)} with full indicators."
        sentiment_result = sentiment.analyze(coin_summary, market_summary)
        sentiment_score = sentiment_result.get("sentiment_score", 0)

        selection = selector.select_coins(top_coins, indicators)
        recommendations = selection.get("recommendations", [])

        regime_summary = ""
        for rec in recommendations[:3]:
            sym = rec.get("symbol", "")
            ind = indicators.get(sym, {})
            if ind:
                r = regime.detect_regime(sym, ind)
                regime_summary += f"{sym}: {r.get('regime', 'unknown')} | "

        today = datetime.now().strftime("%Y-%m-%d")
        with Session(db_engine) as session:
            import json
            existing = session.exec(
                select(DailyStat).where(DailyStat.date == today)
            ).first()

            picks_json = json.dumps([r.get("symbol") for r in recommendations])

            if existing:
                existing.sentiment_score = sentiment_score
                existing.regime_summary = regime_summary
                existing.ai_coin_picks = picks_json
                session.add(existing)
            else:
                stat = DailyStat(
                    date=today,
                    sentiment_score=sentiment_score,
                    regime_summary=regime_summary,
                    ai_coin_picks=picks_json,
                )
                session.add(stat)
            session.commit()

        logger.info(
            f"AI analysis done: sentiment={sentiment_score:.2f}, "
            f"recommended={[r.get('symbol') for r in recommendations]}, "
            f"regime={regime_summary.strip()}"
        )

        if recommendations:
            rec = recommendations[0]
            logger.info(
                f"Top pick: {rec.get('symbol')} "
                f"(score={rec.get('suitability_score', 0):.2f}, "
                f"range={rec.get('lower_buffer_pct', 5)}%/{rec.get('upper_buffer_pct', 5)}%)"
            )

        if dashboard:
            dashboard.set_ai_recommendations(recommendations)

    except Exception as e:
        logger.error(f"AI analysis job failed: {e}", exc_info=True)


def main():
    setup_logging()
    logger = logging.getLogger("main")

    print("=" * 50)
    print("  GridBot - OKX Spot Grid Trading Bot")
    print("=" * 50)

    check_config()

    os.makedirs("data", exist_ok=True)
    db_engine = init_db(settings.DATABASE_URL)
    logger.info("Database initialized")

    exchange = OKXExchange()
    risk = RiskManager(
        max_investment_per_grid=settings.MAX_INVESTMENT_PER_GRID_USDT,
        max_total_exposure=settings.MAX_TOTAL_EXPOSURE_USDT,
        daily_loss_limit=settings.DAILY_LOSS_LIMIT_USDT,
        stop_loss_breach_pct=settings.STOP_LOSS_BREACH_PCT,
        max_concurrent_grids=settings.MAX_CONCURRENT_GRIDS,
        coin_whitelist=settings.COIN_WHITELIST,
    )

    engine = GridEngine(exchange, risk, db_engine)

    recovered = engine.recover_all()
    if recovered:
        logger.info(f"Recovered {recovered} grids from previous session")

    collector = MarketDataCollector(exchange)
    sentiment = SentimentAnalyzer()
    selector = CoinSelector()
    regime = RegimeDetector()
    alert_manager = AlertManager(
        telegram_token=settings.TELEGRAM_BOT_TOKEN,
        telegram_chat_id=settings.TELEGRAM_CHAT_ID,
    )

    from api.server import DashboardAPI, api_app
    dashboard = DashboardAPI(engine, db_engine, exchange=exchange)

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        engine.tick_all,
        "interval",
        seconds=settings.ENGINE_TICK_INTERVAL_S,
        id="engine_tick",
    )
    scheduler.add_job(
        ai_analysis_job,
        "interval",
        hours=settings.AI_COIN_SELECTION_INTERVAL_H,
        args=[engine, collector, sentiment, selector, regime, db_engine, dashboard],
        id="ai_analysis",
    )
    scheduler.start()
    logger.info(
        f"Scheduler started: tick={settings.ENGINE_TICK_INTERVAL_S}s, "
        f"AI={settings.AI_COIN_SELECTION_INTERVAL_H}h"
    )

    if settings.TELEGRAM_BOT_TOKEN:
        alert_manager.send("GridBot 已启动", f"Sandbox: {settings.OKX_SANDBOX}", "info")

    def shutdown():
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        engine.pause_all()
        if settings.TELEGRAM_BOT_TOKEN:
            try:
                alert_manager.send("GridBot 已停止", "服务正常关闭", "info")
            except Exception:
                pass
        db_engine.dispose()
        logger.info("GridBot stopped")

    signal.signal(signal.SIGINT, lambda sig, frame: shutdown())
    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown())

    logger.info(f"Dashboard: http://{settings.HOST}:{settings.PORT}")

    try:
        uvicorn.run(api_app, host=settings.HOST, port=settings.PORT, log_level="info")
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()


if __name__ == "__main__":
    main()
