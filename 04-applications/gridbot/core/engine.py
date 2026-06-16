import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import Session, select

from config.settings import settings
from core.exchange import OKXExchange
from core.grid import GridLevelData, create_grid_levels, find_level_index_for_price
from core.risk import RiskManager
from data.db import (
    Grid,
    GridLevel,
    GridStatus,
    Trade,
)

logger = logging.getLogger(__name__)

ORDER_CONFIRM_MAX_RETRIES = 5
ORDER_CONFIRM_DELAY_S = 0.5


class SingleGridEngine:
    def __init__(
        self,
        grid_id: int,
        symbol: str,
        lower: float,
        upper: float,
        count: int,
        investment: float,
        qty_per_grid: float,
        grid_type: str,
        exchange: OKXExchange,
        risk: RiskManager,
        db_engine,
    ):
        self.grid_id = grid_id
        self.symbol = symbol
        self.lower = lower
        self.upper = upper
        self.count = count
        self.investment = investment
        self.qty_per_grid = qty_per_grid
        self.grid_type = grid_type
        self.exchange = exchange
        self.risk = risk
        self.db_engine = db_engine

        self.status = GridStatus.IDLE
        self.levels: List[GridLevelData] = []
        self.realized_pnl: float = 0.0

    def _place_order_safe(self, side: str, price: float) -> Optional[str]:
        for attempt in range(ORDER_CONFIRM_MAX_RETRIES):
            try:
                amount = self.exchange.round_amount(self.symbol, self.qty_per_grid)
                price = self.exchange.round_price(self.symbol, price)

                if amount <= 0:
                    logger.error(f"Grid {self.grid_id}: zero amount for {side} at {price}")
                    return None

                order = self.exchange.create_limit_order(self.symbol, side, amount, price)

                time.sleep(ORDER_CONFIRM_DELAY_S)

                confirmed = self.exchange.fetch_order(order["id"], self.symbol)
                status = confirmed.get("status", "")
                if status in ("open", "closed"):
                    return order["id"]

                if status in ("canceled", "expired", "rejected"):
                    logger.warning(
                        f"Grid {self.grid_id}: {side} at {price} {status}, "
                        f"retry {attempt + 1}/{ORDER_CONFIRM_MAX_RETRIES}"
                    )
                    continue

                return order["id"]

            except Exception as e:
                logger.warning(
                    f"Grid {self.grid_id}: {side} at {price} failed "
                    f"(attempt {attempt + 1}): {e}"
                )
                if attempt < ORDER_CONFIRM_MAX_RETRIES - 1:
                    time.sleep(1.0)

        logger.error(f"Grid {self.grid_id}: {side} at {price} failed after all retries")
        return None

    def start(self) -> bool:
        if self.status not in (GridStatus.IDLE, GridStatus.STOPPED):
            logger.warning(f"Grid {self.grid_id} cannot start from {self.status}")
            return False

        try:
            with Session(self.db_engine) as session:
                db_levels = (
                    session.exec(
                        select(GridLevel)
                        .where(GridLevel.grid_id == self.grid_id)
                        .order_by(GridLevel.level_index)
                    )
                    .all()
                )

            if db_levels:
                self.levels = [
                    GridLevelData(
                        index=dl.level_index,
                        price=dl.price,
                        buy_order_id=dl.buy_order_id,
                        sell_order_id=dl.sell_order_id,
                        buy_filled=dl.buy_filled,
                        sell_filled=dl.sell_filled,
                    )
                    for dl in db_levels
                ]
            else:
                self.levels = create_grid_levels(
                    self.lower, self.upper, self.count, self.grid_type
                )
                with Session(self.db_engine) as session:
                    for lv in self.levels:
                        db_level = GridLevel(
                            grid_id=self.grid_id,
                            level_index=lv.index,
                            price=lv.price,
                        )
                        session.add(db_level)
                    session.commit()

            self._cancel_existing_orders()

            ticker = self.exchange.fetch_ticker(self.symbol)
            current = ticker["last"]
            midpoint = find_level_index_for_price(self.levels, current)
            logger.info(f"Grid {self.grid_id} ({self.symbol}): current={current}, midpoint={midpoint}")

            for i, level in enumerate(self.levels):
                if level.buy_filled:
                    continue

                if i < midpoint:
                    order_id = self._place_order_safe("buy", level.price)
                    if order_id:
                        level.buy_order_id = order_id
                        level.buy_filled = False
                        self._update_level_db(level)

                elif i >= midpoint:
                    order_id = self._place_order_safe("sell", level.price)
                    if order_id:
                        level.sell_order_id = order_id
                        level.sell_filled = False
                        self._update_level_db(level)
                    else:
                        level.sell_order_id = None
                        level.sell_filled = False
                        self._update_level_db(level)

            self.status = GridStatus.RUNNING
            self._update_grid_db(started=True)
            logger.info(f"Grid {self.grid_id} ({self.symbol}) started: {self.count} levels")
            return True

        except Exception as e:
            logger.error(f"Failed to start grid {self.grid_id}: {e}")
            self.status = GridStatus.ERROR
            self._update_grid_db()
            return False

    def _cancel_existing_orders(self):
        try:
            open_orders = self.exchange.fetch_open_orders(self.symbol)
            for order in open_orders:
                try:
                    self.exchange.cancel_order(order["id"], self.symbol)
                    logger.info(f"Grid {self.grid_id}: cancelled old order {order['id']}")
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Grid {self.grid_id}: failed to cancel existing orders: {e}")

    def sync_orders_from_exchange(self):
        try:
            open_orders = self.exchange.fetch_open_orders(self.symbol)
            order_map = {o["id"]: o for o in open_orders}

            for level in self.levels:
                if level.buy_order_id and level.buy_order_id not in order_map:
                    order = self.exchange.fetch_order(level.buy_order_id, self.symbol)
                    if order and order.get("status") == "closed" and order.get("filled", 0) > 0:
                        level.buy_filled = True
                        level.buy_filled_at = datetime.now()
                        self._update_level_db(level)
                        logger.info(f"Grid {self.grid_id}: recovered buy fill at {level.price}")

                if level.sell_order_id and level.sell_order_id not in order_map:
                    order = self.exchange.fetch_order(level.sell_order_id, self.symbol)
                    if order and order.get("status") == "closed" and order.get("filled", 0) > 0:
                        level.sell_filled = True
                        level.sell_filled_at = datetime.now()
                        self._update_level_db(level)

                        if level.index > 0:
                            buy_level = self.levels[level.index - 1]
                            if buy_level.buy_filled:
                                profit = (level.price - buy_level.price) * self.qty_per_grid
                                profit_pct = (level.price - buy_level.price) / buy_level.price
                                self.realized_pnl += profit
                                self._record_trade(
                                    buy_level.price, level.price,
                                    self.qty_per_grid, profit, profit_pct,
                                )
                                buy_level.buy_filled = False
                                buy_level.buy_order_id = None

                                buy_order_id = self._place_order_safe("buy", buy_level.price)
                                if buy_order_id:
                                    buy_level.buy_order_id = buy_order_id
                                    self._update_level_db(buy_level)

                                logger.info(
                                    f"Grid {self.grid_id}: recovered sell fill at {level.price}, "
                                    f"PnL: {profit:+.4f}"
                                )

                        level.sell_filled = False
                        level.sell_order_id = None

            self._update_grid_db()

        except Exception as e:
            logger.error(f"Grid {self.grid_id}: sync failed: {e}")

    def tick(self):
        if self.status != GridStatus.RUNNING:
            return

        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            current = ticker["last"]

            stop_check = self.risk.check_stop_loss(self.symbol, self.lower, current)
            if not stop_check.allowed:
                logger.warning(f"Grid {self.grid_id} stop-loss triggered: {stop_check.reason}")
                self.emergency_stop(current)
                return

            for i, level in enumerate(self.levels):
                if level.buy_order_id and not level.buy_filled:
                    self._check_buy_fill(i, level)

                if level.sell_order_id and not level.sell_filled:
                    self._check_sell_fill(i, level)

            self._update_grid_db()

        except Exception as e:
            logger.error(f"Tick error grid {self.grid_id}: {e}")

    def _check_buy_fill(self, index: int, level: GridLevelData):
        try:
            order = self.exchange.fetch_order(level.buy_order_id, self.symbol)
            if order["status"] == "closed" and order.get("filled", 0) > 0:
                level.buy_filled = True
                level.buy_filled_at = datetime.now()
                self._update_level_db(level)
                logger.info(f"Grid {self.grid_id}: BUY filled at {level.price}")

                if index + 1 < len(self.levels):
                    sell_level = self.levels[index + 1]
                    if not sell_level.sell_order_id:
                        order_id = self._place_order_safe("sell", sell_level.price)
                        if order_id:
                            sell_level.sell_order_id = order_id
                            self._update_level_db(sell_level)
        except Exception as e:
            logger.error(f"Check buy fill error grid {self.grid_id} level {index}: {e}")

    def _check_sell_fill(self, index: int, level: GridLevelData):
        try:
            order = self.exchange.fetch_order(level.sell_order_id, self.symbol)
            if order["status"] == "closed" and order.get("filled", 0) > 0:
                level.sell_filled = True
                level.sell_filled_at = datetime.now()
                self._update_level_db(level)

                if index > 0:
                    buy_level = self.levels[index - 1]
                    if buy_level.buy_filled:
                        profit = (level.price - buy_level.price) * self.qty_per_grid
                        profit_pct = (level.price - buy_level.price) / buy_level.price

                        self.realized_pnl += profit
                        self.risk.accumulate_daily_loss(-profit if profit < 0 else 0)

                        self._record_trade(
                            buy_level.price, level.price,
                            self.qty_per_grid, profit, profit_pct,
                        )

                        buy_level.buy_filled = False
                        buy_level.buy_order_id = None
                        buy_level.sell_filled = False
                        buy_level.sell_order_id = None

                        order_id = self._place_order_safe("buy", buy_level.price)
                        if order_id:
                            buy_level.buy_order_id = order_id
                            self._update_level_db(buy_level)
                        else:
                            logger.error(f"Grid {self.grid_id}: failed to place buy at {buy_level.price}")

                        logger.info(
                            f"Grid {self.grid_id}: SELL filled at {level.price}, "
                            f"PnL: {profit:+.4f} USDT ({profit_pct:+.4%})"
                        )

                level.sell_filled = False
                level.sell_order_id = None
                self._update_level_db(level)

        except Exception as e:
            logger.error(f"Check sell fill error grid {self.grid_id} level {index}: {e}")

    def pause(self) -> bool:
        if self.status != GridStatus.RUNNING:
            return False
        self.status = GridStatus.PAUSED
        self._update_grid_db()
        logger.info(f"Grid {self.grid_id} paused")
        return True

    def stop(self) -> bool:
        try:
            self.exchange.cancel_all_orders(self.symbol)
            self.status = GridStatus.STOPPED
            self._update_grid_db(stopped=True)
            logger.info(f"Grid {self.grid_id} stopped, PnL: {self.realized_pnl:.4f}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop grid {self.grid_id}: {e}")
            return False

    def emergency_stop(self, current_price: float):
        try:
            self.exchange.cancel_all_orders(self.symbol)

            base_held = sum(
                1 for lv in self.levels if lv.buy_filled
            ) * self.qty_per_grid
            if base_held > 0:
                amount = self.exchange.round_amount(self.symbol, base_held)
                if amount > 0:
                    self.exchange.create_market_order(self.symbol, "sell", amount)
                    logger.info(
                        f"Grid {self.grid_id}: emergency sold {amount} {self.symbol} at ~{current_price}"
                    )

            self.status = GridStatus.STOPPED
            self._update_grid_db(stopped=True)
            logger.warning(f"Grid {self.grid_id} emergency stopped")
        except Exception as e:
            logger.error(f"Emergency stop failed for grid {self.grid_id}: {e}")

    def get_summary(self) -> dict:
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            current = ticker["last"]
        except Exception:
            current = 0.0

        filled_buys = sum(1 for lv in self.levels if lv.buy_filled)
        base_held = filled_buys * self.qty_per_grid
        unrealized = base_held * current if base_held > 0 else 0.0

        return {
            "id": self.grid_id,
            "symbol": self.symbol,
            "status": self.status.value,
            "grid_type": self.grid_type,
            "upper": self.upper,
            "lower": self.lower,
            "grid_count": self.count,
            "current_price": current,
            "realized_pnl": round(self.realized_pnl, 4),
            "unrealized_value": round(unrealized, 4),
            "filled_buys": filled_buys,
            "investment": self.investment,
        }

    def _update_level_db(self, level: GridLevelData):
        with Session(self.db_engine) as session:
            db_level = session.exec(
                select(GridLevel).where(
                    GridLevel.grid_id == self.grid_id,
                    GridLevel.level_index == level.index,
                )
            ).first()
            if db_level:
                db_level.buy_order_id = level.buy_order_id
                db_level.sell_order_id = level.sell_order_id
                db_level.buy_filled = level.buy_filled
                db_level.sell_filled = level.sell_filled
                db_level.buy_filled_at = level.buy_filled_at
                db_level.sell_filled_at = level.sell_filled_at
                session.add(db_level)
                session.commit()

    def _update_grid_db(self, started: bool = False, stopped: bool = False):
        with Session(self.db_engine) as session:
            grid = session.get(Grid, self.grid_id)
            if grid:
                grid.status = self.status.value
                grid.realized_pnl = self.realized_pnl
                grid.last_tick_at = datetime.now()
                if started:
                    grid.started_at = datetime.now()
                if stopped:
                    grid.stopped_at = datetime.now()
                session.add(grid)
                session.commit()

    def _record_trade(
        self,
        buy_price: float,
        sell_price: float,
        quantity: float,
        profit: float,
        profit_pct: float,
    ):
        with Session(self.db_engine) as session:
            trade = Trade(
                grid_id=self.grid_id,
                symbol=self.symbol,
                buy_price=buy_price,
                sell_price=sell_price,
                quantity=quantity,
                profit=profit,
                profit_pct=profit_pct,
                buy_filled_at=datetime.now(),
                sell_filled_at=datetime.now(),
            )
            session.add(trade)
            session.commit()


class GridEngine:
    def __init__(
        self,
        exchange: OKXExchange,
        risk_manager: RiskManager,
        db_engine,
    ):
        self.exchange = exchange
        self.risk = risk_manager
        self.db_engine = db_engine
        self._active: Dict[int, SingleGridEngine] = {}

    def recover_all(self):
        with Session(self.db_engine) as session:
            grids = session.exec(
                select(Grid).where(
                    Grid.status.in_([GridStatus.RUNNING.value, GridStatus.PAUSED.value])
                )
            ).all()

        restored = 0
        for grid in grids:
            try:
                levels = []
                with Session(self.db_engine) as session:
                    db_levels = (
                        session.exec(
                            select(GridLevel)
                            .where(GridLevel.grid_id == grid.id)
                            .order_by(GridLevel.level_index)
                        )
                        .all()
                    )
                    levels = [
                        GridLevelData(
                            index=lv.level_index,
                            price=lv.price,
                            buy_order_id=lv.buy_order_id,
                            sell_order_id=lv.sell_order_id,
                            buy_filled=lv.buy_filled,
                            sell_filled=lv.sell_filled,
                            buy_filled_at=lv.buy_filled_at,
                            sell_filled_at=lv.sell_filled_at,
                        )
                        for lv in db_levels
                    ]

                engine = SingleGridEngine(
                    grid.id, grid.symbol, grid.lower_price, grid.upper_price,
                    grid.grid_count, grid.investment_amount, grid.quantity_per_grid,
                    grid.grid_type, self.exchange, self.risk, self.db_engine,
                )
                engine.status = GridStatus(grid.status)
                engine.realized_pnl = grid.realized_pnl
                engine.levels = levels

                engine.sync_orders_from_exchange()

                self._active[grid.id] = engine
                restored += 1
                logger.info(f"Recovered grid {grid.id} ({grid.symbol}): status={engine.status.value}")

            except Exception as e:
                logger.error(f"Failed to recover grid {grid.id}: {e}")

        logger.info(f"Recovery complete: {restored}/{len(grids)} grids restored")
        return restored

    def create_grid(
        self,
        symbol: str,
        upper: float,
        lower: float,
        grid_count: int,
        investment: float,
        grid_type: str = "arithmetic",
    ) -> Optional[int]:
        if not symbol or "/" not in symbol:
            logger.error(f"Invalid symbol: {symbol}")
            return None
        if upper <= lower:
            logger.error(f"Invalid price range: upper={upper} <= lower={lower}")
            return None
        if lower <= 0:
            logger.error(f"Lower price must be positive: {lower}")
            return None
        if grid_count < 2:
            logger.error(f"Grid count must be >= 2: {grid_count}")
            return None
        if grid_count > settings.MAX_GRIDS_PER_COIN:
            logger.error(f"Grid count exceeds max: {grid_count} > {settings.MAX_GRIDS_PER_COIN}")
            return None
        if investment <= 0:
            logger.error(f"Investment must be positive: {investment}")
            return None
        if grid_type not in ("arithmetic", "geometric"):
            logger.error(f"Invalid grid type: {grid_type}")
            return None

        check = self.risk.can_create_grid(
            symbol, investment, current_grids, total_exposure
        )
        if not check.allowed:
            logger.warning(f"Risk check failed: {check.reason}")
            return None

        ticker = self.exchange.fetch_ticker(symbol)
        current_price = ticker["last"]
        quote_per_grid, base_per_grid = self.risk.calculate_position_size(
            grid_count, investment, current_price
        )
        qty_per_grid = self.exchange.round_amount(symbol, base_per_grid)

        if qty_per_grid <= 0:
            logger.error(f"Cannot create grid: qty_per_grid={qty_per_grid} (investment too small?)")
            return None

        with Session(self.db_engine) as session:
            grid = Grid(
                symbol=symbol,
                grid_type=grid_type,
                status=GridStatus.IDLE.value,
                upper_price=upper,
                lower_price=lower,
                grid_count=grid_count,
                investment_amount=investment,
                quantity_per_grid=qty_per_grid,
            )
            session.add(grid)
            session.commit()
            session.refresh(grid)

            levels = create_grid_levels(lower, upper, grid_count, grid_type)
            for lv in levels:
                db_level = GridLevel(
                    grid_id=grid.id,
                    level_index=lv.index,
                    price=lv.price,
                )
                session.add(db_level)
            session.commit()

            grid_id = grid.id

        engine = SingleGridEngine(
            grid_id, symbol, lower, upper, grid_count,
            investment, qty_per_grid, grid_type,
            self.exchange, self.risk, self.db_engine,
        )
        self._active[grid_id] = engine
        logger.info(f"Grid {grid_id} created: {symbol} [{lower}, {upper}] x{grid_count}")
        return grid_id

    def start_grid(self, grid_id: int) -> bool:
        if grid_id not in self._active:
            loaded = self._load_from_db(grid_id)
            if not loaded:
                return False
        return self._active[grid_id].start()

    def pause_grid(self, grid_id: int) -> bool:
        engine = self._active.get(grid_id)
        return engine.pause() if engine else False

    def pause_all(self):
        for engine in self._active.values():
            if engine.status == GridStatus.RUNNING:
                engine.pause()
        logger.warning("All grids paused (circuit breaker)")

    def stop_grid(self, grid_id: int) -> bool:
        engine = self._active.get(grid_id)
        return engine.stop() if engine else False

    def tick_all(self):
        for grid_id, engine in list(self._active.items()):
            try:
                engine.tick()
            except Exception as e:
                logger.error(f"Tick error grid {grid_id}: {e}")

    def get_summary(self, grid_id: int) -> Optional[dict]:
        engine = self._active.get(grid_id)
        return engine.get_summary() if engine else None

    def get_all_summaries(self) -> List[dict]:
        return [e.get_summary() for e in self._active.values()]

    def get_active_count(self) -> int:
        return sum(1 for e in self._active.values() if e.status == GridStatus.RUNNING)

    def get_total_pnl(self) -> float:
        return sum(e.realized_pnl for e in self._active.values())

    def _load_from_db(self, grid_id: int) -> bool:
        with Session(self.db_engine) as session:
            grid = session.get(Grid, grid_id)
            if not grid:
                return False

            levels = (
                session.exec(
                    select(GridLevel)
                    .where(GridLevel.grid_id == grid_id)
                    .order_by(GridLevel.level_index)
                )
                .all()
            )

        engine = SingleGridEngine(
            grid_id, grid.symbol, grid.lower_price, grid.upper_price,
            grid.grid_count, grid.investment_amount, grid.quantity_per_grid,
            grid.grid_type, self.exchange, self.risk, self.db_engine,
        )
        engine.status = GridStatus(grid.status)
        engine.realized_pnl = grid.realized_pnl
        engine.levels = [
            GridLevelData(
                index=lv.level_index,
                price=lv.price,
                buy_order_id=lv.buy_order_id,
                sell_order_id=lv.sell_order_id,
                buy_filled=lv.buy_filled,
                sell_filled=lv.sell_filled,
                buy_filled_at=lv.buy_filled_at,
                sell_filled_at=lv.sell_filled_at,
            )
            for lv in levels
        ]
        self._active[grid_id] = engine
        return True
