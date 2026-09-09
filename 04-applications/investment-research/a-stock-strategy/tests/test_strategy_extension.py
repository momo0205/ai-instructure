from pathlib import Path

import pytest

import strategy.registry as registry
from strategy import workbench
from strategy.strategies.fixed import FixedAssetStrategy

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def third_strategy(monkeypatch):
    assert hasattr(registry, 'StrategyDefinition'), 'strategy extension definition is missing'
    monkeypatch.setattr(registry, '_REGISTRY', dict(registry._REGISTRY))
    definition = registry.StrategyDefinition(
        id='third', name='Third', description='Different parameter names', version='test-1',
        parameters=[dict(name='assets', type='array', default=['588000.SH']),
                    dict(name='history', type='integer', default=3, min=1, max=252)],
        constructor=lambda assets, history: FixedAssetStrategy(assets[0]),
        symbol_selector=lambda parameters: parameters['assets'],
        warmup=lambda parameters: parameters['history'],
    )
    registry.register_strategy(definition)
    return definition


def test_registered_strategy_runs_with_its_own_parameters(third_strategy, tmp_path):
    result = workbench.execute(ROOT, {'strategy_id': 'third'}, tmp_path)
    assert result['equity'] and result['trades']
    assert result['request']['parameters'] == {'assets': ['588000.SH'], 'history': 3}
    assert result['metadata']['strategy_version'] == 'test-1'
    assert any('588000.SH has 0/3 prior sessions' in w for w in result['warnings'])
    warmed = workbench.execute(ROOT, {'strategy_id': 'third', 'start': '2024-02-01'}, tmp_path/'warm')
    assert not any('warmup' in w for w in warmed['warnings'])


@pytest.mark.parametrize('parameters', [None, {'unknown': 1}, {'history': True},
    {'history': 1.5}, {'history': float('nan')}, {'assets': '588000.SH'},
    {'assets': []}, {'assets': ['588000.SH', '588000.SH']}, {'assets': ['MISSING']}])
def test_registered_strategy_rejects_invalid_parameters(third_strategy, parameters):
    with pytest.raises(ValueError):
        workbench.validate_request(ROOT, {'strategy_id': 'third', 'parameters': parameters})


def test_definition_defaults_and_inputs_are_isolated(third_strategy):
    first = third_strategy.normalize_parameters({})
    first['assets'].append('510300.SH')
    assert third_strategy.normalize_parameters({})['assets'] == ['588000.SH']
    supplied = {'assets': ['588000.SH']}
    normalized = third_strategy.normalize_parameters(supplied)
    normalized['assets'].clear()
    assert supplied['assets'] == ['588000.SH']
    directory = registry.catalog()
    next(x for x in directory if x['id'] == 'third')['parameters'][0]['default'].clear()
    assert third_strategy.normalize_parameters({})['assets'] == ['588000.SH']


def test_registration_rejects_duplicates_and_unknown_ids(third_strategy):
    assert registry.get_strategy_definition('third') is third_strategy
    with pytest.raises(ValueError, match='already registered'):
        registry.register_strategy(third_strategy)
    for invalid in ('missing', [], None):
        with pytest.raises(ValueError, match='unknown strategy_id'):
            registry.get_strategy_definition(invalid)


@pytest.mark.parametrize('weights', [{'bad': 1}, {'momentum': True}, {'volume': float('inf')}, []])
def test_rank_definition_rejects_invalid_weights(weights):
    assert hasattr(registry, 'get_strategy_definition'), 'definition lookup is missing'
    with pytest.raises(ValueError, match='weights'):
        registry.get_strategy_definition('cross_sectional_rank').normalize_parameters({'weights': weights})


def test_rank_definition_partial_weights_and_default_isolation():
    assert hasattr(registry, 'get_strategy_definition'), 'definition lookup is missing'
    definition = registry.get_strategy_definition('cross_sectional_rank')
    params = definition.normalize_parameters({'weights': {'momentum': 2}})
    assert params['weights'] == dict(momentum=2., reversal=1., volatility=-.25, volume=0.)
    params['candidate_symbols'].clear()
    params['weights']['reversal'] = 99
    assert definition.normalize_parameters({})['weights']['reversal'] == 1.
    assert definition.normalize_parameters({})['candidate_symbols']


@pytest.mark.parametrize('kind, invalid', [('string', 1), ('array', 'x'), ('object', []), ('boolean', 1), ('unsupported', 'x')])
def test_definition_rejects_invalid_schema_types(third_strategy, kind, invalid):
    third_strategy.parameters = [dict(name='option', type=kind, default=invalid)]
    with pytest.raises(ValueError, match='option'):
        third_strategy.normalize_parameters({})


@pytest.mark.parametrize('kind, valid', [('string', 'x'), ('array', []), ('object', {}), ('boolean', True)])
def test_definition_accepts_schema_types(third_strategy, kind, valid):
    third_strategy.parameters = [dict(name='option', type=kind, default=valid)]
    assert third_strategy.normalize_parameters({}) == {'option': valid}


@pytest.mark.parametrize('invalid', [-1, True, 1.5, float('nan'), '3', 3.0])
def test_definition_rejects_invalid_warmup(third_strategy, invalid):
    third_strategy.warmup = lambda parameters: invalid
    with pytest.raises(ValueError, match='warmup'):
        third_strategy.warmup_sessions({})


def test_definition_accepts_zero_and_unbounded_warmup(third_strategy):
    for sessions in (0, 1000000):
        third_strategy.warmup = lambda parameters: sessions
        assert third_strategy.warmup_sessions({}) == sessions
