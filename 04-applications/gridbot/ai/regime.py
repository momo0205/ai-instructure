import json
import logging
from typing import Dict

from openai import OpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a market regime analyst for crypto grid trading.
Classify the market regime and assess grid trading suitability.

Return JSON:
{
  "regime": "ranging" | "weak_trending" | "strong_trending" | "volatile",
  "grid_suitable": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "string",
  "risk_level": "low" | "medium" | "high"
}
Only return valid JSON."""


class RegimeDetector:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        self.model = settings.LLM_MODEL

    def detect_regime(self, symbol: str, indicators: dict) -> dict:
        adx = indicators.get("adx", 0)
        bb_width = indicators.get("bb_width", 0)
        vol_trend = indicators.get("volume_trend", 1.0)

        if adx > 30:
            return {
                "regime": "strong_trending",
                "grid_suitable": False,
                "confidence": 0.9,
                "reasoning": f"ADX={adx:.1f} indicates strong trend, grid not recommended",
                "risk_level": "high",
            }

        if adx > 25:
            return {
                "regime": "weak_trending",
                "grid_suitable": False,
                "confidence": 0.75,
                "reasoning": f"ADX={adx:.1f} indicates trending, grid risky",
                "risk_level": "medium",
            }

        if adx < 20 and 0.03 < bb_width < 0.20:
            return {
                "regime": "ranging",
                "grid_suitable": True,
                "confidence": 0.85,
                "reasoning": f"ADX={adx:.1f} shows ranging, BB_width={bb_width:.4f} is moderate",
                "risk_level": "low",
            }

        return self._llm_detect(symbol, indicators)

    def _llm_detect(self, symbol: str, indicators: dict) -> dict:
        try:
            prompt = f"""Analyze market regime for {symbol}:

ADX: {indicators.get('adx', 0):.2f}
BB Width: {indicators.get('bb_width', 0):.4f}
Volatility: {indicators.get('volatility', 0):.4f}
Volume Trend: {indicators.get('volume_trend', 1.0):.2f}
24h Change: {indicators.get('price_change_24h', 0):.2f}%

Is this suitable for grid trading?"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=400,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw) if raw else {}
            logger.info(f"Regime for {symbol}: {result.get('regime')}")
            return result

        except Exception as e:
            logger.error(f"Regime detection failed for {symbol}: {e}")
            return {
                "regime": "unknown",
                "grid_suitable": True,
                "confidence": 0.3,
                "reasoning": f"LLM unavailable, ADX={indicators.get('adx', 0):.1f}",
                "risk_level": "medium",
            }
