import json
import logging
from typing import Dict

from openai import OpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a crypto market sentiment analyst.
Analyze the given data and return a JSON object:
{
  "sentiment_score": float (-1 extreme fear to 1 extreme greed),
  "confidence": float (0 to 1),
  "market_mood": "fearful" | "cautious" | "neutral" | "optimistic" | "greedy",
  "key_factors": [string, ...],
  "risk_advice": string
}
Only return valid JSON."""


class SentimentAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        self.model = settings.LLM_MODEL

    def analyze(self, top_movers: str, market_summary: str, news: str = "") -> dict:
        try:
            prompt = f"""Analyze crypto market sentiment:

Top movers (24h):
{top_movers}

Market summary:
{market_summary}

News:
{news or 'No news available'}

Assess current conditions for grid trading."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw) if raw else {}
            logger.info(f"Sentiment: {result.get('market_mood')} ({result.get('sentiment_score')})")
            return result

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "market_mood": "unknown",
                "key_factors": ["API error"],
                "risk_advice": "Use default risk parameters",
            }
