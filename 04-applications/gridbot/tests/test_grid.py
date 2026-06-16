import pytest
from core.grid import (
    calculate_arithmetic_grid,
    calculate_geometric_grid,
    create_grid_levels,
    find_level_index_for_price,
)
from core.risk import RiskManager, RiskCheckResult


class TestGridCalculations:
    def test_arithmetic_grid_even_spacing(self):
        prices = calculate_arithmetic_grid(100.0, 200.0, 11)
        assert len(prices) == 11
        assert prices[0] == 100.0
        assert prices[-1] == 200.0
        step = prices[1] - prices[0]
        for i in range(len(prices) - 1):
            assert abs((prices[i + 1] - prices[i]) - step) < 1e-10

    def test_geometric_grid_positive_ratio(self):
        prices = calculate_geometric_grid(100.0, 200.0, 11)
        assert len(prices) == 11
        assert prices[0] == 100.0
        assert prices[-1] == pytest.approx(200.0, rel=1e-10)
        ratio = prices[1] / prices[0]
        assert ratio > 1.0
        for i in range(len(prices) - 1):
            assert abs(prices[i + 1] / prices[i] - ratio) < 1e-10

    def test_geometric_grid_zero_price(self):
        with pytest.raises(ValueError):
            calculate_geometric_grid(0, 100, 5)

    def test_create_grid_levels_default_arithmetic(self):
        levels = create_grid_levels(100, 200, 11)
        assert len(levels) == 11
        assert levels[0].price == 100.0
        assert levels[-1].price == pytest.approx(200.0, rel=1e-10)
        assert levels[0].index == 0

    def test_create_grid_levels_geometric(self):
        levels = create_grid_levels(100, 200, 11, "geometric")
        assert len(levels) == 11
        assert levels[0].price == 100.0
        assert levels[-1].price == pytest.approx(200.0, rel=1e-10)

    def test_find_level_index_closest(self):
        levels = create_grid_levels(100, 200, 11)
        idx = find_level_index_for_price(levels, 153)
        assert idx == 5


class TestRiskManager:
    def test_whitelist_check(self):
        rm = RiskManager(1000, 5000, 200, 0.03, 5, ["BTC/USDT"])
        assert rm.can_create_grid("BTC/USDT", 500, 0, 0).allowed
        assert not rm.can_create_grid("ETH/USDT", 500, 0, 0).allowed

    def test_max_investment_check(self):
        rm = RiskManager(500, 5000, 200, 0.03, 5, ["BTC/USDT"])
        assert not rm.can_create_grid("BTC/USDT", 600, 0, 0).allowed

    def test_max_concurrent_check(self):
        rm = RiskManager(1000, 5000, 200, 0.03, 2, ["BTC/USDT"])
        assert not rm.can_create_grid("BTC/USDT", 500, 2, 500).allowed

    def test_total_exposure_check(self):
        rm = RiskManager(1000, 2000, 200, 0.03, 5, ["BTC/USDT"])
        assert not rm.can_create_grid("BTC/USDT", 500, 0, 1800).allowed

    def test_stop_loss_not_triggered(self):
        rm = RiskManager(1000, 5000, 200, 0.03, 5, ["BTC/USDT"])
        result = rm.check_stop_loss("BTC/USDT", 60000, 59000)
        assert result.allowed

    def test_stop_loss_triggered(self):
        rm = RiskManager(1000, 5000, 200, 0.03, 5, ["BTC/USDT"])
        result = rm.check_stop_loss("BTC/USDT", 60000, 57000)
        assert not result.allowed

    def test_daily_loss_limit(self):
        rm = RiskManager(1000, 5000, 100, 0.03, 5, ["BTC/USDT"])
        assert rm.can_create_grid("BTC/USDT", 500, 0, 0).allowed
        rm.accumulate_daily_loss(101)
        assert not rm.can_create_grid("BTC/USDT", 500, 0, 0).allowed

    def test_position_size_calculation(self):
        rm = RiskManager(1000, 5000, 200, 0.03, 5, ["BTC/USDT"])
        quote, base = rm.calculate_position_size(10, 1000, 50000)
        assert quote == 100.0
        assert base == 0.002
