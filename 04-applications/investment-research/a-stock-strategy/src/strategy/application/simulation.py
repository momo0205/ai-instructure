"""所有入口共用的回测运行合同；输入适配和报告格式由调用方负责。"""
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
from strategy.backtesting.engine import BacktestEngine, BacktestResult
from strategy.backtesting.evaluation import Metrics, evaluate


@dataclass(frozen=True)
class SimulationPlan:
    market: pd.DataFrame
    strategy: Any
    engine_options: dict
    profile: str
    start: date | None = None
    end: date | None = None


@dataclass(frozen=True)
class SimulationOutcome:
    engine: BacktestEngine
    result: BacktestResult
    metrics: Metrics


def run_simulation(plan: SimulationPlan) -> SimulationOutcome:
    """集中构造引擎、执行和评估；旧配置差异必须由适配器显式提供。"""
    engine = BacktestEngine(**plan.engine_options)
    result = engine.run(plan.market, plan.strategy, start=plan.start, end=plan.end)
    return SimulationOutcome(engine, result, evaluate(result))
