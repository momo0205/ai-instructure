"""The library is a shared contract for the API, chart and future strategies."""
import math

import pandas as pd
import pytest


def test_catalog_groups_source_and_derived_indicators_and_is_a_copy():
    from strategy.indicators import indicator_catalog
    entries = indicator_catalog()
    assert {(entry['id'], entry['category']) for entry in entries} >= {
        ('ohlc', 'price'), ('sma', 'trend'), ('ema', 'trend'),
        ('bollinger', 'volatility'), ('volume', 'volume'),
        ('amount', 'volume'), ('volume_sma', 'volume'),
    }
    assert all({'name', 'description', 'version', 'formula', 'inputs', 'outputs',
                'parameters', 'warmup', 'panel', 'kind'} <= entry.keys() for entry in entries)
    entries[0]['name'] = 'changed'
    assert indicator_catalog()[0]['name'] != 'changed'


@pytest.mark.parametrize('items', [
    [{'instance_id': 'x', 'id': 'unknown'}],
    [{'instance_id': 'x', 'id': 'sma', 'parameters': {'window': 1}}],
    [{'instance_id': 'x', 'id': 'sma', 'parameters': {'window': True}}],
    [{'instance_id': 'x', 'id': 'bollinger', 'parameters': {'multiplier': float('nan')}}],
    [{'instance_id': 'x', 'id': 'bollinger', 'parameters': {'multiplier': 10**1000}}],
    [{'instance_id': 'x', 'id': 'sma'}, {'instance_id': 'x', 'id': 'ema'}],
    [{'instance_id': '../x', 'id': 'sma'}],
    [{'instance_id': str(i), 'id': 'sma'} for i in range(13)],
])
def test_invalid_instances_are_rejected(items):
    from strategy.indicators import normalize_instances
    with pytest.raises(ValueError):
        normalize_instances(items)


def test_normalized_instances_have_defaults_and_independent_ids():
    from strategy.indicators import normalize_instances
    actual = normalize_instances([
        {'instance_id': 'fast', 'id': 'sma', 'parameters': {'window': 2}},
        {'instance_id': 'slow', 'id': 'sma'},
    ])
    assert actual == [
        {'instance_id': 'fast', 'id': 'sma', 'parameters': {'window': 2}},
        {'instance_id': 'slow', 'id': 'sma', 'parameters': {'window': 20}},
    ]


def test_hand_calculated_series_and_population_bollinger():
    from strategy.indicators import calculate_series, normalize_instances
    rows = [dict(date=f'2026-01-0{i}', close=float(i), volume=float(i-1)) for i in range(1, 6)]
    instances = normalize_instances([
        {'instance_id': 's', 'id': 'sma', 'parameters': {'window': 2}},
        {'instance_id': 'e', 'id': 'ema', 'parameters': {'window': 2}},
        {'instance_id': 'b', 'id': 'bollinger', 'parameters': {'window': 2, 'multiplier': 2}},
        {'instance_id': 'v', 'id': 'volume_sma', 'parameters': {'window': 2}},
    ])
    result = calculate_series(rows, instances)
    assert result['s'][0]['values']['value'] is None
    assert result['s'][1]['values']['value'] == 1.5
    assert result['e'][1]['values']['value'] == 1.5
    assert result['e'][2]['values']['value'] == pytest.approx(2.5)
    assert result['b'][1]['values'] == {'middle': 1.5, 'upper': 2.5, 'lower': .5}
    assert result['v'][1]['values']['value'] == .5
    assert all(item['reason'] == '' for item in result['e'][1:])


def test_missing_close_resets_ema_and_does_not_hide_valid_volume():
    from strategy.indicators import calculate_series, normalize_instances
    rows = [dict(close=1, volume=0), dict(close=2, volume=2),
            dict(close=None, volume=4), dict(close=4, volume=6), dict(close=5, volume=8)]
    instances = normalize_instances([
        {'instance_id': 'e', 'id': 'ema', 'parameters': {'window': 2}},
        {'instance_id': 's', 'id': 'sma', 'parameters': {'window': 2}},
        {'instance_id': 'v', 'id': 'volume_sma', 'parameters': {'window': 2}},
    ])
    result = calculate_series(rows, instances)
    assert result['e'][2]['values']['value'] is None
    assert result['e'][3]['values']['value'] is None
    assert result['e'][4]['values']['value'] == 4.5
    assert result['s'][4]['values']['value'] == 4.5
    assert result['v'][2]['values']['value'] == 3
    assert result['s'][2]['reason'] == 'invalid_close'


def test_existing_moving_average_contract_is_preserved():
    from strategy.indicators import simple_moving_average, calculate_series, normalize_instances
    history = pd.DataFrame([
        dict(date=pd.Timestamp('2026-01-01'), symbol='A', close=1),
        dict(date=pd.Timestamp('2026-01-02'), symbol='A', close=2),
    ])
    old = simple_moving_average(history, 'A', pd.Timestamp('2026-01-02'), 2)
    new = calculate_series([{'close': 1}, {'close': 2}], normalize_instances([
        {'instance_id': 'ma', 'id': 'sma', 'parameters': {'window': 2}},
    ]))['ma'][-1]
    assert old.value == new['values']['value'] == 1.5


def test_large_finite_inputs_do_not_crash_or_emit_infinity():
    from strategy.indicators import calculate_series, normalize_instances
    items = normalize_instances([{'instance_id':'s','id':'sma','parameters':{'window':2}},
                                 {'instance_id':'b','id':'bollinger','parameters':{'window':2,'multiplier':10}}])
    result = calculate_series([{'close':1e308},{'close':1}],items)
    assert math.isfinite(result['s'][-1]['values']['value'])
    assert result['b'][-1]['values']['upper'] is None
    assert result['b'][-1]['reason'] == 'nonfinite_result'
