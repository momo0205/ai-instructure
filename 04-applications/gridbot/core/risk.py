import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str | None = None


class RiskManager:
    def __init__(
        self,
        max_investment_per_grid: float,
        max_total_exposure: float,
        daily_loss_limit: float,
        stop_loss_breach_pct: float,
        max_concurrent_grids: int,
        coin_whitelist: List[str],
    ):
        self.max_investment_per_grid = max_investment_per_grid
        self.max_total_exposure = max_total_exposure
        self.daily_loss_limit = daily_loss_limit
        self.stop_loss_breach_pct = stop_loss_breach_pct
        self.max_concurrent_grids = max_concurrent_grids
        self.coin_whitelist = coin_whitelist
        self._daily_loss_accumulated: float = 0.0
        self._daily_loss_date: str = ""

    def can_create_grid(
        self,
        symbol: str,
        investment: float,
        current_grid_count: int,
        current_total_exposure: float,
    ) -> RiskCheckResult:
        if symbol not in self.coin_whitelist:
            return RiskCheckResult(False, f"{symbol} not in whitelist")

        if current_grid_count >= self.max_concurrent_grids:
            return RiskCheckResult(False, f"Max {self.max_concurrent_grids} grids reached")

        if investment > self.max_investment_per_grid:
            return RiskCheckResult(
                False,
                f"Investment {investment} > max {self.max_investment_per_grid}",
            )

        if current_total_exposure + investment > self.max_total_exposure:
            return RiskCheckResult(False, "Would exceed max total exposure")

        if self._is_daily_loss_exceeded():
            return RiskCheckResult(False, "Daily loss limit reached")

        return RiskCheckResult(True)

    def check_stop_loss(
        self, symbol: str, lower_bound: float, current_price: float
    ) -> RiskCheckResult:
        breach_pct = (lower_bound - current_price) / lower_bound
        if breach_pct > self.stop_loss_breach_pct:
            return RiskCheckResult(
                False,
                f"Stop-loss: price {current_price} breached {breach_pct:.2%} below lower {lower_bound}",
            )
        return RiskCheckResult(True)

    def accumulate_daily_loss(self, loss: float):
        today = datetime.now().strftime("%Y-%m-%d")
        if self._daily_loss_date != today:
            self._daily_loss_accumulated = 0.0
            self._daily_loss_date = today
        self._daily_loss_accumulated += abs(loss)
        if self._daily_loss_accumulated >= self.daily_loss_limit:
            logger.warning(
                f"Daily loss limit reached: {self._daily_loss_accumulated:.2f} >= {self.daily_loss_limit}"
            )

    def _is_daily_loss_exceeded(self) -> bool:
        return self._daily_loss_accumulated >= self.daily_loss_limit

    def check_circuit_breaker(self, price_change_pct: float, volatility: float) -> RiskCheckResult:
        if abs(price_change_pct) > 10.0:
            return RiskCheckResult(
                False,
                f"Circuit breaker: {price_change_pct:+.1f}% flash crash/spike detected",
            )
        if volatility > 5.0:
            return RiskCheckResult(
                False,
                f"Circuit breaker: volatility {volatility:.1f} too extreme for grid",
            )
        return RiskCheckResult(True)

    def calculate_position_size(
        self,
        grid_count: int,
        total_investment: float,
        current_price: float,
    ) -> tuple[float, float]:
        quote_per_grid = total_investment / grid_count
        base_per_grid = quote_per_grid / current_price
        return quote_per_grid, base_per_grid
