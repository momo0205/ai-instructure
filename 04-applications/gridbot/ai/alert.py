import json
import logging
from urllib.request import Request, urlopen

from config.settings import settings

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, telegram_token: str = "", telegram_chat_id: str = ""):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

    def send(self, title: str, message: str, level: str = "info"):
        logger.info(f"ALERT [{level}] {title}: {message}")
        self._send_telegram(f"[{level.upper()}] {title}\n{message}")

    def on_stop_loss(self, grid_id: int, symbol: str, reason: str):
        self.send("止损触发", f"Grid #{grid_id} ({symbol})\n{reason}", "error")

    def on_circuit_breaker(self, reason: str):
        self.send("熔断触发", reason, "error")

    def on_grid_error(self, grid_id: int, symbol: str, error: str):
        self.send("网格异常", f"Grid #{grid_id} ({symbol})\n{error}", "error")

    def on_daily_summary(self, pnl: float, trades: int):
        emoji = "🟢" if pnl >= 0 else "🔴"
        self.send(
            "每日总结",
            f"{emoji} PnL: {pnl:+.4f} USDT\n📊 交易: {trades} 笔",
            "info",
        )

    def _send_telegram(self, text: str):
        if not self.telegram_token or not self.telegram_chat_id:
            return

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            body = json.dumps({
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML",
            }).encode()
            req = Request(url, data=body, headers={"Content-Type": "application/json"})
            urlopen(req, timeout=10)
        except Exception as e:
            logger.warning(f"Telegram alert failed: {e}")
