"""任务作用域内的进度事件；CLI无监听时为空操作，不污染持久结果或计算参数。"""
from contextlib import contextmanager
from contextvars import ContextVar

_listener = ContextVar('backtest_progress_listener', default=None)


class TaskCancelled(Exception):
    """工作线程在安全的计算阶段边界响应用户取消。"""


@contextmanager
def progress_scope(listener):
    token = _listener.set(listener)
    try:
        yield
    finally:
        _listener.reset(token)


def report_progress(stage, completed, total):
    listener = _listener.get()
    if listener is not None:
        listener(stage=stage, completed=completed, total=total)
