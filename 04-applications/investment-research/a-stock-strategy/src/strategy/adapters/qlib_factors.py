"""隔离 Qlib 因子计算，明确错误、取消和输入输出审计。"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

from strategy.application.progress import report_progress
from strategy.validation import UserError


def run_worker(command, folder, timeout=120):
    """日志留在任务目录；轮询可响应取消，任何退出路径都回收子进程。"""
    process = None
    started = time.monotonic()
    with (Path(folder)/'worker.log').open('w') as log:
        try:
            process = subprocess.Popen(command, cwd=folder, stdout=log, stderr=log)
            while process.poll() is None:
                report_progress('factors', 0, 1)
                if time.monotonic()-started > timeout:
                    raise UserError('QLIB_FAILED', 'Qlib 因子计算超时，请缩小区间或候选数量后重试。')
                time.sleep(.1)
            if process.returncode:
                raise UserError('QLIB_FAILED', 'Qlib 因子计算失败；任务日志已保留，请检查独立环境和输入行情。')
        except OSError:
            raise UserError('QLIB_UNAVAILABLE', 'Qlib 独立解释器不可启动，请检查运行环境。') from None
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()


def validate_output(payload, symbols, dates, lookback):
    try:
        if payload['version'] != '0.9.7' or payload['expression'] != f'$close/Ref($close, {lookback})-1':
            raise ValueError
        seen = set()
        for row in payload['rows']:
            key = (row['date'], row['symbol'])
            value = row['score']
            if key in seen or row['date'] not in dates or row['symbol'] not in symbols:
                raise ValueError
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
                raise ValueError
            seen.add(key)
        if seen != {(day,symbol) for day in dates for symbol in symbols}:
            raise ValueError
        return payload['rows']
    except (KeyError, TypeError, ValueError):
        raise UserError('QLIB_FAILED', 'Qlib 因子输出不完整或格式不合法，未执行回测。') from None


def compute_factors(market, symbols, lookback, output_dir):
    default = Path(__file__).resolve().parents[3]/'reports/qlib-env/bin/python'
    # 不 resolve 解释器符号链接，否则可能绕开 venv 导致依赖无法找到。
    python = Path(os.path.abspath(os.environ.get('A_STOCK_QLIB_PYTHON',str(default))))
    if not python.is_file():
        raise UserError('QLIB_UNAVAILABLE', '未安装 Qlib 独立环境；请配置 A_STOCK_QLIB_PYTHON，或选择本地动量策略。')
    folder = Path(output_dir).resolve()/'qlib'
    folder.mkdir(parents=True,exist_ok=True)
    frame = market[['date','symbol','close']].copy()
    frame['date'] = frame.date.astype(str).str[:10]
    frame.to_csv(folder/'input.csv', index=False)
    (folder/'request.json').write_text(json.dumps({'symbols':symbols,'lookback':lookback}))
    run_worker([str(python),str(Path(__file__).with_name('qlib_worker.py')),str(folder)],folder)
    try:
        payload = json.loads((folder/'output.json').read_text())
    except (OSError, ValueError):
        raise UserError('QLIB_FAILED', 'Qlib 未生成有效的因子结果，未执行回测。') from None
    rows = validate_output(payload,symbols,sorted(frame.date.unique()),lookback)
    report_progress('factors',1,1)
    return rows, dict(backend='qlib', version=payload['version'], expression=payload['expression'],
        calendar='shared market sessions; missing bars are not filled', precision='Qlib float32 provider',
        input_sha256=hashlib.sha256((folder/'input.csv').read_bytes()).hexdigest(),
        output_sha256=hashlib.sha256((folder/'output.json').read_bytes()).hexdigest(), rows=rows)
