"""The package split preserves execution and captures all application sources."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def test_split_execution_matches_legacy(tmp_path):
    from strategy import workbench
    from strategy.application.backtests import execute

    request = {'dataset_id': 'mvp_sample', 'start': '2024-02-01'}
    legacy = workbench.execute(ROOT, request, tmp_path / 'legacy')
    actual = execute(ROOT, request, tmp_path / 'new')
    assert actual == legacy
    assert json.loads((tmp_path / 'new' / 'result.json').read_text()) == actual


def test_snapshot_fallback_captures_complete_package(tmp_path):
    from strategy.application.backtests import execute

    root = tmp_path / 'project'
    shutil.copytree(ROOT / 'data' / 'mvp_sample', root / 'data' / 'mvp_sample')
    output = tmp_path / 'run'
    result = execute(root, {}, output)
    for relative in ('application/requests.py', 'application/backtests.py', 'storage/snapshots.py', '__init__.py'):
        name = 'code/' + relative
        frozen = output / 'snapshot' / name
        assert frozen.is_file()
        assert hashlib.sha256(frozen.read_bytes()).hexdigest() == result['metadata']['hashes'][name]
    request_bytes = (output / 'snapshot' / 'request.json').read_bytes()
    assert hashlib.sha256(request_bytes).hexdigest() == result['metadata']['hashes']['request.json']
