from strategy.tradability import DailyBarStatusProvider, execution_block
import numpy as np
import pytest


@pytest.mark.parametrize('value', [1, np.int64(1), np.bool_(True), '1', 'true'])
def test_explicit_true_flags_block_regardless_of_scalar_type(value):
    status = DailyBarStatusProvider().read({'open': 10, 'is_suspended': value})
    assert execution_block(status, 'buy', 'stock') == 'suspended'


def test_unknown_flags_remain_unknown_and_approximate_policy_allows():
    status = DailyBarStatusProvider().read({'open': 10, 'is_suspended': False})
    assert status.suspended is None
    assert execution_block(status, 'buy', 'stock') == ''


def test_verified_negative_flag_is_distinct_from_unknown():
    status = DailyBarStatusProvider(flags_verified=True).read({'open': 10, 'is_suspended': False})
    assert status.suspended is False


def test_status_rules_are_directional_and_do_not_use_future_prices():
    provider = DailyBarStatusProvider()
    status = provider.read({'open': 10, 'limit_down': True, 'volume': 0, 'close': 0})
    assert execution_block(status, 'buy', 'stock') == ''
    assert execution_block(status, 'sell', 'stock') == 'limit_down'
    assert execution_block(provider.read({'open': 10, 'is_suspended': True}), 'buy', 'stock') == 'suspended'
    assert execution_block(provider.read(None), 'sell', 'stock') == 'missing_row'
