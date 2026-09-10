"""旧平铺模块名的兼容映射；新业务代码只使用规范包路径。"""
from importlib import import_module
import sys

ALIASES = {'registry': 'strategies.registry',
 'data': 'market_data.csv',
 'breadth': 'market_data.breadth',
 'data_sources': 'market_data.sources',
 'dataset_repository': 'market_data.repository',
 'instrument_catalog': 'market_data.catalog',
 'market_provider': 'market_data.provider',
 'market_download': 'market_data.tencent',
 'ingest': 'market_data.ingest',
 'backtest': 'backtesting.engine',
 'fees': 'backtesting.fees',
 'signals': 'backtesting.signals',
 'evaluation': 'backtesting.evaluation',
 'tradability': 'backtesting.tradability',
 'reporting': 'storage.reports',
 'recommendation': 'application.recommendation',
 'comparison': 'application.comparison',
 'llm': 'application.llm',
 'config': 'interfaces.cli.config',
 'cli': 'interfaces.cli.main',
 'web': 'interfaces.web.server',
 'jobs': 'application.jobs',
 'instruments': 'application.downloads',
 'workbench': 'application.backtests'}


def install():
    package = sys.modules['strategy']
    for old, new in ALIASES.items():
        module = import_module('strategy.' + new)
        sys.modules['strategy.' + old] = module
        setattr(package, old, module)
