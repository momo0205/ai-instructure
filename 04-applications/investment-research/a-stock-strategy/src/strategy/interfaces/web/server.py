"""本机工作台 HTTP 边界。业务逻辑位于 workbench/jobs，页面与 CLI 共用引擎。

仅绑定回环地址，并校验 Host/Origin，避免网页跨站请求触发本机任务。
不开放任意路径或 Python 代码执行；静态资源只有显式白名单。
"""
from __future__ import annotations

from strategy.application.diagnostics import diagnostic, error_response, exception_diagnostic
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from strategy.application.research import ResearchService, ResearchUnavailable


def static_file(path: str) -> Path:
    files = {'/': 'index.html', '/index.html': 'index.html',
             '/app.js': 'app.js', '/tabs.js': 'tabs.js', '/style.css': 'style.css',
             '/instrument-options.js': 'instrument-options.js', '/research.js': 'research.js', '/studies.js': 'studies.js', '/compositions.js': 'compositions.js', '/research-inputs.js': 'research-inputs.js', '/explanations.js': 'explanations.js', '/data-management.js': 'data-management.js'}
    if path not in files:
        raise ValueError('资源不存在')
    return Path(__file__).parent / 'static' / files[path]


def check_host(headers, port: int) -> None:
    if headers.get('Host') not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
        raise ValueError('仅支持本机访问')


def check_write_request(headers, port: int) -> None:
    """浏览器写操作需要同源；无 Origin 的本机 CLI 请求仍允许使用 JSON。"""
    check_host(headers, port)
    origin = headers.get('Origin')
    if origin is not None and origin != f"http://{headers.get('Host')}":
        raise ValueError('拒绝跨源操作')
    if headers.get('Content-Type', '').split(';')[0] != 'application/json':
        raise ValueError('请求必须使用 application/json')
    size = int(headers.get('Content-Length', '0'))
    if not 0 < size <= 65536:
        raise ValueError('请求大小不合法（上限 64 KB）')


def dispatch(method, path, payload, root, manager, downloads=None, studies=None, foundations=None):
    """返回 (HTTP 状态码, JSON 对象)，便于脱离网络测试业务路由。"""
    try:
        if method == 'GET':
            if path == '/api/foundation-updates' and foundations is not None:
                return 200, foundations.list()
            if path == '/api/data-management':
                from strategy.application.data_management import DataManagementService
                import os
                # 先读取任务状态，避免目录扫描后恰好完成发布而提前停止轮询。
                updates = foundations.list() if foundations is not None else []
                result = DataManagementService(root).catalog()
                result['foundation_updates'] = updates
                result['foundation_credentials_configured'] = bool(os.environ.get('TUSHARE_TOKEN','').strip())
                return 200, result
            if path.startswith('/api/data-assets/') and path.count('/') == 3:
                from strategy.application.data_management import DataManagementService
                return 200, DataManagementService(root).detail(path.split('/')[3])
            if path == '/api/studies' and studies is not None:
                return 200, studies.list()
            if path.startswith('/api/studies/') and path.count('/') == 3 and studies is not None:
                return 200, studies.get(path.split('/')[3])
            if path == '/api/research-experiments':
                return 200, ResearchService(manager).list()
            if path == '/api/experiments':
                return 200, manager.experiments.config()
            if path == '/api/instruments':
                from strategy.application.downloads import instrument_catalog
                return 200, instrument_catalog(root)
            if path == '/api/downloads' and downloads is not None:
                return 200, downloads.list()
            if path == '/api/strategies':
                from strategy.strategies.registry import catalog
                return 200, catalog()
            if path == '/api/datasets':
                from strategy.application.backtests import datasets
                return 200, datasets(root)
            if path == '/api/jobs':
                return 200, manager.list()
            if path.startswith('/api/jobs/') and path.endswith('/input-dataset') and path.count('/') == 4:
                from strategy.application.direct_inputs import input_dataset
                return 200, input_dataset(manager,path.split('/')[3])
            if path.startswith('/api/jobs/') and path.count('/') == 3:
                job = manager.get(path.rsplit('/', 1)[1])
                return (200, job) if job is not None else (404, error_response(diagnostic('NOT_FOUND')))
        if method == 'POST':
            if not isinstance(payload, dict):
                return 400, error_response(diagnostic('INVALID_REQUEST'))
            if path == '/api/foundation-updates' and foundations is not None:
                return 202, foundations.submit(payload)
            if path.startswith('/api/data-assets/') and path.endswith('/research') and path.count('/') == 4:
                from strategy.application.data_management import DataManagementService
                if payload:
                    raise ValueError('研究准备不接受额外参数，请使用资产共同覆盖区间')
                return 201, DataManagementService(root).prepare_research(path.split('/')[3])
            if path == '/api/jobs/from-selection':
                from strategy.application.direct_inputs import submit_selection
                return 202, submit_selection(manager,payload)
            if path in ('/api/compositions/preview', '/api/compositions'):
                from strategy.application.compositions import CompositionService
                service = CompositionService(root)
                return (200, service.preview(payload)) if path.endswith('/preview') else (201, service.create(payload))
            if path == '/api/studies' and studies is not None:
                return 202, studies.submit(payload)
            if path.startswith('/api/studies/') and path.endswith('/cancel') and path.count('/') == 4 and studies is not None:
                return 200, studies.cancel(path.split('/')[3])
            if path == '/api/downloads' and downloads is not None:
                return 202, downloads.submit(payload)
            if path == '/api/jobs':
                return 202, manager.submit(payload)
            if path.startswith('/api/jobs/') and path.endswith('/experiment-label') and path.count('/') == 4:
                return 200, ResearchService(manager).label(path.split('/')[3], payload)
            if path.startswith('/api/jobs/') and path.endswith('/experiment') and path.count('/') == 4:
                return 202, manager.sync_experiment(path.split('/')[3])
            if path.startswith('/api/jobs/') and path.endswith('/cancel') and path.count('/') == 4:
                return 200, manager.cancel(path.split('/')[3])
        return 404, error_response(diagnostic('NOT_FOUND'))
    except ResearchUnavailable:
        return 503, error_response(diagnostic('EXPERIMENT_STORE_UNAVAILABLE'))
    except (ValueError, TypeError) as error:
        return 400, error_response(exception_diagnostic(error, 'request'))
    except KeyError:
        return 404, error_response(diagnostic('NOT_FOUND'))
    except Exception:
        logging.getLogger(__name__).exception('接口处理失败：%s %s', method, path)
        return 500, error_response(diagnostic('INTERNAL_ERROR'))


def serve(root: Path, port: int = 8765, state_dir: Path | None = None, *,
          experiment_python=None, experiment_ui_url='http://127.0.0.1:5000'):
    """启动单用户服务；浏览器关闭不会终止后台任务，Ctrl-C 关闭服务。"""
    from strategy.application.jobs import JobManager
    root = Path(root).resolve()
    manager = None
    downloads = None
    studies = None
    foundations = None

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, data, content_type='application/json; charset=utf-8'):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False, allow_nan=False, default=str).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            try:
                check_host(self.headers, self.server.server_port)
                path = urlsplit(self.path).path
                if path.startswith('/api/'):
                    self.send(*dispatch('GET', path, None, root, manager, downloads, studies, foundations))
                else:
                    resource = static_file(path)
                    mime = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css'}[resource.suffix]
                    self.send(200, resource.read_bytes(), mime + '; charset=utf-8')
            except (ValueError, FileNotFoundError) as error:
                self.send(404, error_response(diagnostic('INVALID_REQUEST')))

        def do_POST(self):
            try:
                check_write_request(self.headers, self.server.server_port)
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.send(*dispatch('POST', urlsplit(self.path).path, payload, root, manager, downloads, studies, foundations))
            except (ValueError, UnicodeDecodeError) as error:
                self.send(400, error_response(diagnostic('INVALID_REQUEST')))

    server = None
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        # 先占用端口，再恢复任务，避免第二次启动篡改正在运行的服务状态。
        manager = JobManager(root, state_dir or root / 'reports' / 'workbench',
                             experiment_python=experiment_python, experiment_ui_url=experiment_ui_url)
        from strategy.application.studies import StudyManager
        studies = StudyManager(manager)
        from strategy.application.downloads import DownloadManager
        downloads = DownloadManager(root, state_dir or root / 'reports' / 'workbench')
        from strategy.application.foundation_updates import FoundationUpdateManager
        foundations = FoundationUpdateManager(root, state_dir or root / 'reports' / 'workbench')
        print(f'回测工作台：http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.server_close()
        if studies is not None:
            studies.close()
        if manager is not None:
            manager.close()
        if downloads is not None:
            downloads.close()
        if foundations is not None:
            foundations.close()
