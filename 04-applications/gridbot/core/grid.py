from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class GridLevelData:
    index: int
    price: float
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    buy_filled: bool = False
    sell_filled: bool = False
    buy_filled_at: Optional[datetime] = None
    sell_filled_at: Optional[datetime] = None


def calculate_arithmetic_grid(lower: float, upper: float, count: int) -> List[float]:
    step = (upper - lower) / (count - 1)
    return [lower + i * step for i in range(count)]


def calculate_geometric_grid(lower: float, upper: float, count: int) -> List[float]:
    if lower <= 0 or upper <= 0:
        raise ValueError("Prices must be positive for geometric grid")
    ratio = (upper / lower) ** (1.0 / (count - 1))
    return [lower * (ratio**i) for i in range(count)]


def create_grid_levels(
    lower: float,
    upper: float,
    count: int,
    grid_type: str = "arithmetic",
) -> List[GridLevelData]:
    if grid_type == "geometric":
        prices = calculate_geometric_grid(lower, upper, count)
    else:
        prices = calculate_arithmetic_grid(lower, upper, count)

    return [GridLevelData(index=i, price=prices[i]) for i in range(count)]


def find_level_index_for_price(levels: List[GridLevelData], price: float) -> int:
    if not levels:
        return 0
    closest = 0
    min_diff = abs(levels[0].price - price)
    for i, level in enumerate(levels):
        diff = abs(level.price - price)
        if diff < min_diff:
            min_diff = diff
            closest = i
    return closest
