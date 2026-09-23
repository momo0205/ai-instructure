"""两种入口共享请求服务；旧TOML通过显式适配保留历史模型。"""
import json
from pathlib import Path

from strategy.application.backtests import execute

ROOT = Path(__file__).resolve().parents[1]


def test_cli_request_matches_web_application(tmp_path, capsys):
    from strategy.interfaces.cli.main import main
    request = {'dataset_id':'mvp_sample', 'strategy_id':'cross_sectional_rank'}
    file = tmp_path/'request.json'
    file.write_text(json.dumps(request))
    assert main(['backtest','--request',str(file),'--project-root',str(ROOT),'--output',str(tmp_path/'cli')]) == 0
    cli = json.loads((tmp_path/'cli/result.json').read_text())
    web = execute(ROOT, request, tmp_path/'web')
    assert cli == web
    assert json.loads(capsys.readouterr().out)['output'] == str(tmp_path/'cli')


def test_legacy_adapter_and_workbench_share_runtime(tmp_path, monkeypatch):
    import strategy.application.simulation as simulation
    from strategy.application.legacy_config import load_inputs, execute_config
    seen = []
    original = simulation.run_simulation
    def capture(plan):
        seen.append(plan)
        return original(plan)
    monkeypatch.setattr(simulation, 'run_simulation', capture)
    execute(ROOT, {}, tmp_path/'web')
    config, data = load_inputs(ROOT/'configs/mvp.toml')
    execute_config(config, data, tmp_path/'legacy')
    assert len(seen) == 2
    assert seen[0].profile == 'workbench'
    assert seen[1].profile == 'legacy_toml'


def test_application_has_no_cli_import_dependency():
    import ast
    for path in (ROOT/'src/strategy/application').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith('strategy.interfaces'), path.name
