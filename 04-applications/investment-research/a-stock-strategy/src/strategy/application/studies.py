"""持有期批量研究：前段选参后锁定一个候选，再运行后段验证。"""
from datetime import datetime, timezone, date
import json
import logging
import math
import hashlib
from pathlib import Path
import queue
import shutil
import threading
import uuid

from strategy.application.requests import validate_request
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.validation import UserError

ACTIVE = ('queued', 'selecting', 'validating')


def choose_configuration(rows):
    """固定规则只读取选参指标；零完整交易不能凭现金收益成为赢家。"""
    if any(row['status'] != 'succeeded' for row in rows):
        raise ValueError('候选回测未全部成功')
    eligible = [row for row in rows if row['metrics']['trade_count'] > 0
                and math.isfinite(row['metrics']['cumulative_return'])]
    if not eligible:
        return None
    winner = max(eligible, key=lambda row: (row['metrics']['cumulative_return'], -row['holding_period_days'], -row.get('lookback', 0)))
    return {key:winner[key] for key in ('holding_period_days','lookback') if key in winner}


def choose_candidate(rows):
    # 保留原单参数调用合同。
    winner = choose_configuration(rows)
    return winner['holding_period_days'] if winner else None


def candidate_request(request, candidate):
    result = request | {'holding_period_days':candidate['holding_period_days']}
    if 'lookback' in candidate:
        result['parameters'] = request['parameters'] | {'lookback':candidate['lookback']}
    return result


class StudyStopped(Exception):
    pass


class StudyManager:
    """仅编排已有回测任务。磁盘保存分组关系，关机/重启不自动重跑后段。"""
    def __init__(self, jobs):
        self.jobs = jobs
        self.root = Path(jobs.state_dir) / 'studies'
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._queue = queue.Queue()
        self._records = {}
        for path in self.root.glob('*/state.json'):
            try:
                record = json.loads(path.read_text())
                if not isinstance(record, dict) or record.get('id') != path.parent.name or not isinstance(record.get('training'), list) or 'status' not in record or 'created_at' not in record:
                    raise ValueError('invalid study record')
            except (OSError, ValueError):
                logging.getLogger(__name__).exception('批量记录损坏：%s', path.parent.name)
                record = dict(id=path.parent.name, status='failed', training=[], validation=None,
                              holding_periods=[], created_at='', message='此批量记录损坏，其他回测不受影响。')
            self._records[record['id']] = record
            if record['status'] in ACTIVE:
                self._safe_save(record | {'status': 'interrupted', 'message': '服务重启，本组已中断；保留已完成结果，请新建研究。'})
        # 追回“任务已入队、成员关联尚未落盘”时崩溃留下的任务。
        recovering = {key for key,row in self._records.items() if row['status'] in ('interrupted','failed')}
        if recovering:
            for path in (Path(jobs.state_dir)/'runs').glob('*/study.json'):
                try:
                    context = json.loads(path.read_text()); key = context['id']
                    if key not in recovering:
                        continue
                    job = jobs.cancel(path.parent.name)
                    row = self._records[key]
                    known = row['training'] + ([row.get('validation')] if row.get('validation') else [])
                    if not any(m['job_id'] == job['id'] for m in known):
                        member = dict(job_id=job['id'], holding_period_days=job['request']['holding_period_days'],
                                      status=job['status'], metrics=job.get('result',{}).get('metrics'))
                        if 'lookback' in context.get('candidate',{}):
                            member['lookback'] = context['candidate']['lookback']
                        changes = {'training':row['training']+[member]} if context['phase']=='selection' else {'validation':member}
                        self._safe_save(row | changes)
                except Exception:
                    logging.getLogger(__name__).exception('批量成员恢复失败：%s', path.parent.name)
        self._thread = threading.Thread(target=self._worker, name='study-coordinator', daemon=True)
        self._thread.start()

    def _save(self, record):
        path = self.root / record['id'] / 'state.json'
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=False, allow_nan=False))
        temporary.replace(path)
        self._records[record['id']] = record

    def _safe_save(self, record):
        """错误收尾不能再因磁盘故障杀死协调线程；保留内存状态供页面读取。"""
        try:
            self._save(record)
        except OSError:
            self._records[record['id']] = record
            logging.getLogger(__name__).exception('批量状态暂未保存：%s', record['id'])

    def _cancel_members(self, record):
        def stop(member):
            try:
                job = self.jobs.cancel(member['job_id'])
                return member | {'status':job['status'], 'metrics':job.get('result',{}).get('metrics')}
            except Exception:
                logging.getLogger(__name__).exception('批量成员取消失败：%s', member['job_id'])
                return member
        return record | {'training':[stop(m) for m in record['training']],
                         'validation':stop(record['validation']) if record.get('validation') else None}

    def get(self, key):
        with self._lock:
            return json.loads(json.dumps(self._records[key]))

    def list(self):
        with self._lock:
            return {'items': [self.get(key) for key in sorted(self._records,
                    key=lambda k: self._records[k]['created_at'], reverse=True)]}

    def submit(self, payload):
        if not isinstance(payload, dict) or set(payload) not in ({'base_job_id', 'holding_periods', 'validation_start'}, {'base_job_id', 'holding_periods', 'validation_start', 'lookbacks'}):
            raise UserError('INVALID_REQUEST', '请提供基础任务、持有天数和后段起始日期')
        holds = payload['holding_periods']
        if not isinstance(holds, list) or not 2 <= len(holds) <= 8 or any(type(n) is not int or not 1 <= n <= 252 for n in holds) or len(set(holds)) != len(holds):
            raise UserError('INVALID_REQUEST', '请选择 2 至 8 个不重复的持有天数（1—252）')
        boundary = payload['validation_start']
        if not isinstance(boundary, str) or date.fromisoformat(boundary).isoformat() != boundary:
            raise UserError('INVALID_REQUEST', '后段起始日期格式不合法')
        base = self.jobs.get(payload['base_job_id'])
        if base['status'] != 'succeeded':
            raise UserError('INVALID_REQUEST', '请从成功回测创建批量研究')
        request = base['request'] | {'effectiveness': False}
        windows = payload.get('lookbacks')
        if 'lookbacks' in payload:
            if request['strategy_id'] not in ('price_momentum','qlib_momentum'):
                raise UserError('INVALID_REQUEST', '当前策略不支持动量窗口网格')
            if not isinstance(windows,list) or not 1 <= len(windows) <= 8 or any(type(n) is not int or not 1 <= n <= 252 for n in windows) or len(set(windows)) != len(windows):
                raise UserError('INVALID_REQUEST', '动量窗口须为 1 至 8 个不重复整数（1—252）')
            if len(windows)*len(holds)>24:
                raise UserError('INVALID_REQUEST', '参数网格最多支持 24 组组合')
        candidates = [dict(holding_period_days=h, lookback=w) for h in holds for w in windows] if windows else [dict(holding_period_days=h) for h in holds]
        snapshot = Path(self.jobs.state_dir) / 'runs' / base['id'] / 'snapshot'
        frame = CsvMarketDataProvider(snapshot / 'market.csv').load()
        dates = sorted(frame.loc[(frame.symbol == '000001.SH') &
                       frame.date.between(request['start'], request['end']), 'date'].dt.strftime('%Y-%m-%d').unique())
        early, late = [d for d in dates if d < boundary], [d for d in dates if d >= boundary]
        if len(early) < 2 or len(late) < 2:
            raise UserError('INVALID_REQUEST', '选参区间和验证区间各至少需要两个交易日，请调整后段开始日')
        key = uuid.uuid4().hex
        project = self.root / key / 'input_project'
        data = project / 'data' / request['dataset_id']
        data.mkdir(parents=True)
        for name in ('market.csv','breadth.csv','manifest.json','market_manifest.json'):
            if (snapshot / name).is_file():
                shutil.copyfile(snapshot / name, data / name)
                expected = base.get('result',{}).get('metadata',{}).get('hashes',{}).get(name)
                if expected and hashlib.sha256((data/name).read_bytes()).hexdigest() != expected:
                    raise UserError('DATA_VALIDATION_FAILED', '基础任务的冻结行情已变化，请核查原始任务数据')
        # 行情取自基础任务，源码一次性捕获；成员任务不再读取可变的项目行情。
        package = Path(__file__).resolve().parents[1]
        for source in package.rglob('*.py'):
            destination = project / 'src' / 'strategy' / source.relative_to(package)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        # 所有请求先验证，避免生成一半任务后才发现某个候选/区间不合法。
        for start, end in ((early[0], early[-1]), (late[0], late[-1])):
            for candidate in candidates:
                validate_request(project, candidate_request(request, candidate) | {'start':start, 'end':end})
        record = dict(id=key, status='queued', base_job_id=base['id'], holding_periods=holds,
                      candidates=candidates, lookbacks=windows, selected_candidate=None,
                      selection_start=early[0], selection_end=early[-1], validation_start=late[0], validation_end=late[-1],
                      selection_rule='highest_cumulative_return_with_completed_trade', selected_holding_period_days=None,
                      training=[], validation=None, created_at=datetime.now(timezone.utc).isoformat(), request=request)
        with self._lock:
            if self._stop.is_set():
                raise ValueError('服务已关闭')
            self._save(record)
            self._queue.put(key)
        return self.get(key)

    def _check(self, key):
        if self._stop.is_set() or self._records[key]['status'] not in ACTIVE:
            raise StudyStopped()

    def _launch(self, key, phase, candidate):
        with self._lock:
            self._check(key)
            row = self._records[key]
            request = candidate_request(row['request'],candidate) | {
                      'start':row['selection_start' if phase == 'selection' else 'validation_start'],
                      'end':row['selection_end' if phase == 'selection' else 'validation_end']}
            context = {'id':key, 'phase':phase, 'selection_rule':row['selection_rule'],
                       'selected_holding_period_days':row['selected_holding_period_days'],
                       'candidate':candidate, 'selected_candidate':row.get('selected_candidate')}
            job = self.jobs.submit_frozen(request, self.root / key / 'input_project', context)
            member = candidate | {'job_id':job['id'], 'status':job['status'], 'metrics':None}
            updated = row | ({'training':row['training']+[member]} if phase=='selection' else {'validation':member})
            try:
                self._save(updated)
            except OSError:
                # 已创建的任务必须保留在内存关联中，交由统一错误收尾取消。
                self._records[key] = updated
                raise
            return member

    def _wait(self, key, phase, member):
        while True:
            with self._lock:
                self._check(key)
            job = self.jobs.get(member['job_id'])
            if job['status'] not in ('queued','running'):
                member = member | {'status':job['status'], 'metrics':job.get('result', {}).get('metrics')}
                with self._lock:
                    self._check(key)
                    row = self._records[key]
                    changes = {'training':[member if m['job_id'] == member['job_id'] else m for m in row['training']]} if phase == 'selection' else {'validation':member}
                    self._save(row | changes)
                return member
            self._stop.wait(.05)

    def _worker(self):
        while not self._stop.is_set():
            key = self._queue.get()
            if key is None:
                return
            try:
                with self._lock:
                    self._check(key)
                    self._save(self._records[key] | {'status':'selecting'})
                row = self.get(key)
                candidates = row.get('candidates') or [dict(holding_period_days=h) for h in row['holding_periods']]
                members = [self._launch(key, 'selection', candidate) for candidate in candidates]
                results = [self._wait(key, 'selection', m) for m in members]
                chosen = choose_configuration(results)
                with self._lock:
                    self._check(key)
                    self._save(self._records[key] | {'selected_holding_period_days':chosen['holding_period_days'] if chosen else None,
                               'selected_candidate':chosen,
                               'status':'validating' if chosen is not None else 'no_candidate',
                               'message':'未发现有完整交易的候选，未运行后段验证。' if chosen is None else ''})
                if chosen is None:
                    continue
                # 选择已落盘，才创建唯一后段任务；后段结果永远不参与 choose_candidate。
                outcome = self._wait(key, 'validation', self._launch(key, 'validation', chosen))
                if outcome['status'] != 'succeeded':
                    raise ValueError('后段验证失败')
                with self._lock:
                    self._check(key)
                    self._save(self._records[key] | {'status':'completed'})
            except StudyStopped:
                pass
            except Exception:
                logging.getLogger(__name__).exception('批量研究失败：%s', key)
                with self._lock:
                    if self._records[key]['status'] in ACTIVE:
                        row = self._cancel_members(self._records[key])
                        self._safe_save(row | {'status':'failed', 'message':'批量研究未完成，请检查成员任务；未据此形成验证结论。'})

    def cancel(self, key, *, interrupted=False):
        with self._lock:
            row = self._records[key]
            if row['status'] in ACTIVE:
                row = self._cancel_members(row)
                self._safe_save(row | {'status':'interrupted' if interrupted else 'cancelled'})
            return self.get(key)

    def close(self):
        with self._lock:
            for key in self._records:
                self.cancel(key, interrupted=True)
            self._stop.set()
            self._queue.put(None)
        self._thread.join()
