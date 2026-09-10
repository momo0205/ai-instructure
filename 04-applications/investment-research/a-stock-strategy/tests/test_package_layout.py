"""目录迁移的兼容合同与资源路径，不只检查文件是否存在。"""
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('legacy, canonical', [
    ('backtest', 'backtesting.engine'), ('registry', 'strategies.registry'),
    ('dataset_repository', 'market_data.repository'), ('market_provider', 'market_data.provider'),
    ('jobs', 'application.jobs'), ('instruments', 'application.downloads'),
    ('workbench', 'application.backtests'), ('web', 'interfaces.web.server'),
    ('cli', 'interfaces.cli.main'),
])
def test_old_import_is_same_module(legacy, canonical):
    assert importlib.import_module('strategy.'+legacy) is importlib.import_module('strategy.'+canonical)


def test_web_resources_live_with_web_package():
    from strategy.interfaces.web.server import static_file
    for url in ['/', '/app.js', '/style.css', '/instrument-options.js']:
        path = static_file(url)
        assert path.is_file()
        assert path.parent == ROOT/'src/strategy/interfaces/web/static'


def test_command_entry_remains_available():
    result = subprocess.run([sys.executable, '-m', 'strategy', 'serve', '--help'],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    assert '--project-root' in result.stdout


def test_cli_default_project_root_survives_move(monkeypatch):
    from strategy.interfaces.cli.main import main
    from strategy.interfaces.web import server
    calls = []
    monkeypatch.setattr(server, 'serve', lambda root, port: calls.append((root, port)))
    assert main(['serve']) == 0
    assert calls == [(ROOT, 8765)]


def test_job_freezes_full_nested_source_tree(tmp_path):
    from strategy.application.jobs import JobManager
    manager = JobManager(ROOT, tmp_path)
    try:
        job = manager.submit({})
    finally:
        manager.close()
    source = tmp_path/'runs'/job['id']/'input_project/src/strategy'
    for name in ['application/backtests.py', 'storage/snapshots.py', 'backtesting/engine.py',
                 'strategies/registry.py', 'market_data/repository.py', '__main__.py']:
        assert (source/name).is_file(), name
