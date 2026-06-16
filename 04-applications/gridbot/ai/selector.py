import json
import logging
from typing import Dict, List

from openai import OpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a crypto grid trading strategist.
Grid trading works best when:
- Asset is ranging/sideways (ADX < 25)
- Volatility is moderate (not too low = no trades, not too high = breakout risk)
- Volume is sufficient for liquidity

Return JSON:
{
  "recommendations": [
    {
      "symbol": "BTC/USDT",
      "suitability_score": 0.85,
      "grid_type": "geometric",
      "upper_buffer_pct": 5,
      "lower_buffer_pct": 5,
      "grid_count": 30,
      "reasoning": "..."
    }
  ],
  "market_overview": "string",
  "risk_warnings": ["string", ...]
}
Only return valid JSON."""


class CoinSelector:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        self.model = settings.LLM_MODEL

    def select_coins(
        self, top_coins: List[dict], indicators: Dict[str, dict]
    ) -> dict:
        try:
            coin_summaries = []
            for coin in top_coins[:20]:
                sym = coin["symbol"]
                ind = indicators.get(sym, {})
                summary = (
                    f"{sym}: price={coin['last']:.4f}, "
                    f"24h_chg={coin['change_24h']:.2f}%, "
                    f"vol={coin['volume_24h']:.0f}, "
                    f"ADX={ind.get('adx', 0):.1f}, "
                    f"BB_w={ind.get('bb_width', 0):.4f}, "
                    f"volat={ind.get('volatility', 0):.4f}, "
                    f"vol_trend={ind.get('volume_trend', 1.0):.2f}"
                )
                coin_summaries.append(summary)

            prompt = f"""Analyze for spot grid trading:

{chr(10).join(coin_summaries)}

ADX < 20 = ranging (good), ADX > 25 = trending (bad)
BB_width 0.05-0.15 = good range
Vol_trend > 1 = increasing interest (good)
24h_chg near 0 = sideways (ideal)

Recommend 3-5 best coins with specific grid parameters."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw) if raw else {}
            recs = result.get("recommendations", [])
            logger.info(f"Coin selection: {len(recs)} recommended: {[r.get('symbol') for r in recs]}")
            return result

        except Exception as e:
            logger.error(f"Coin selection failed: {e}")
            return {
                "recommendations": [],
                "market_overview": "Analysis unavailable",
                "risk_warnings": ["AI analysis failed, manual selection required"],
            }
