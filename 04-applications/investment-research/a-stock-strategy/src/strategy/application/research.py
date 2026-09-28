"""面向中文实验页的用例：复用 MLflow，限制为当前工作台所属实验。"""
import json
import logging
from pathlib import Path
import subprocess


class ResearchUnavailable(RuntimeError):
    """隔离底层环境错误，页面可重试而不泄露第三方日志。"""


class ResearchService:
    def __init__(self, manager):
        self.manager = manager

    def _invoke(self, action, payload):
        tracker = self.manager.experiments
        script = Path(__file__).resolve().parents[1] / 'storage' / 'mlflow_research.py'
        try:
            response = subprocess.run(
                [tracker.python, str(script), str(tracker.root), action],
                input=json.dumps(payload, ensure_ascii=False), text=True, encoding='utf-8',
                capture_output=True, check=True, timeout=60, cwd=tracker.root)
            return json.loads(response.stdout)
        except Exception as error:
            logging.getLogger(__name__).exception('实验库操作失败：%s', action)
            raise ResearchUnavailable('实验库暂时无法访问，请检查实验环境后重试；回测结果仍然保留。') from error

    def list(self):
        enabled = bool(self.manager.experiments.python)
        response = {'enabled': enabled, 'items': [], 'limit': 200}
        if not enabled:
            return response
        # 只取任务摘要，不在列表读取净值/随机实验大数组。
        local = {row['id']: row for row in self.manager.list() if row['status'] == 'succeeded'}
        for run in self._invoke('list', {}):
            job = local.get(run['job_id'])
            if job is not None:
                response['items'].append(dict(run, request=job['request'], created_at=job['created_at']))
        return response

    def label(self, key, payload):
        if not self.manager.experiments.python:
            raise ValueError('实验同步未启用')
        if not isinstance(payload, dict) or set(payload) - {'name', 'notes'}:
            raise ValueError('仅支持编辑名称和备注')
        name, notes = payload.get('name'), payload.get('notes', '')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise ValueError('实验名称须为 1 至 120 个字符')
        if not isinstance(notes, str) or len(notes) > 2000:
            raise ValueError('实验备注须为不超过 2000 个字符的文本')
        job = self.manager.get(key)
        if job is None:
            raise KeyError(key)
        record = self.manager.experiments.view(key)
        if job['status'] != 'succeeded' or record['status'] != 'synced':
            raise ValueError('请先完成实验同步，再编辑名称和备注')
        # run ID 从服务端同步记录获取，拒绝浏览器选择任意 MLflow run。
        return self._invoke('label', {'job_id': key, 'run_id': record['run_id'],
                                     'annotation': {'name': name.strip(), 'notes': notes}})
