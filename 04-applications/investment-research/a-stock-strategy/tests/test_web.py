"""本机 HTTP 边界：写请求不能被其他网站或任意文件路径触发。"""
import io
import json
from pathlib import Path

import pytest


def test_web_static_files_are_allowlisted():
    from strategy.web import static_file
    assert static_file('/').name == 'index.html'
    assert static_file('/app.js').name == 'app.js'
    assert static_file('/tabs.js').is_file()
    for path in ['/../../pyproject.toml', '/api/../.env', '/index.html/other']:
        with pytest.raises(ValueError):
            static_file(path)


def test_web_write_guard_requires_same_origin_json():
    from strategy.web import check_write_request
    valid = {'Host': '127.0.0.1:8765', 'Content-Type': 'application/json',
             'Origin': 'http://127.0.0.1:8765', 'Content-Length': '2'}
    check_write_request(valid, 8765)
    for changed in [{'Origin': 'https://evil.example'}, {'Host': 'evil.example:8765'},
                    {'Content-Type': 'text/plain'}, {'Content-Length': '9999999'}]:
        with pytest.raises(ValueError):
            check_write_request(valid | changed, 8765)


def test_web_routes_use_manager_and_report_errors():
    from strategy.web import dispatch

    class Manager:
        def list(self):
            return [{'id': 'abc', 'status': 'succeeded'}]

        def get(self, key):
            raise KeyError(key)

        def submit(self, request):
            return {'id': 'new', 'request': request, 'status': 'queued'}

    root = Path(__file__).resolve().parents[1]
    assert dispatch('GET', '/api/jobs', None, root, Manager())[0] == 200
    assert dispatch('GET', '/api/jobs/missing', None, root, Manager())[0] == 404
    code, result = dispatch('POST', '/api/jobs', {'strategy_id': 'fixed_asset'}, root, Manager())
    assert code == 202 and result['status'] == 'queued'
    assert dispatch('POST', '/api/jobs', [], root, Manager())[0] == 400
    assert dispatch('GET', '/api/unknown', None, root, Manager())[0] == 404
