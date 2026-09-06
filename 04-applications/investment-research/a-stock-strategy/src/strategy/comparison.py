"""Offline comparison of a fixed ETF and price-feature ETF ranking."""
from __future__ import annotations

import base64
import csv
from dataclasses import asdict
from html import escape
import json
from pathlib import Path

import pandas as pd

from .config import BacktestConfig
from .evaluation import evaluate
from .reporting import write_report
from .strategies.fixed import FixedAssetStrategy
from .strategies.rank import CrossSectionalRankStrategy


def compare(config: BacktestConfig, data: pd.DataFrame, output_dir: str | Path) -> dict:
    from .cli import _engine, _metadata

    out = Path(output_dir)
    params = config.strategy.parameters
    candidates = list(dict.fromkeys(params.get('candidate_symbols') or ['588000.SH']))
    required = set(candidates) | {params.get('symbol', '588000.SH'), config.market.index_symbol}
    missing = required - set(data['symbol'])
    if missing:
        raise ValueError(f"missing comparison market data: {', '.join(sorted(missing))}")
    out.mkdir(parents=True, exist_ok=True)
    rank_keys = {'momentum_window', 'reversal_window', 'volatility_window', 'volume_window', 'weights', 'min_volume'}
    rank_params = {key: value for key, value in params.items() if key in rank_keys}
    strategies = {
        'fixed_asset': FixedAssetStrategy(params.get('symbol', '588000.SH')),
        'cross_sectional_rank': CrossSectionalRankStrategy(candidate_symbols=candidates, **rank_params),
    }
    warnings = list(config.metadata.get('warnings', []))
    all_sessions = set(pd.to_datetime(data['date']).dt.date)
    coverage = {}
    for symbol in sorted(required):
        observed = set(pd.to_datetime(data.loc[data.symbol == symbol, 'date']).dt.date)
        missing_sessions = sorted(all_sessions - observed)
        coverage[symbol] = {'observed_sessions': len(observed), 'missing_sessions': len(missing_sessions)}
        if missing_sessions:
            warnings.append(f'data quality: {symbol} missing {len(missing_sessions)} sessions; zero trades/returns may reflect unavailable data.')
    benchmark_valid = all(item['missing_sessions'] == 0 for item in coverage.values())
    if not benchmark_valid:
        warnings.append('数据覆盖不完整：暂停基准收益与超额收益比较，先补齐行情。')
    if len(candidates) < 2:
        warnings.append('候选池只有一个ETF，无动态比较意义；评分策略还受特征预热窗口影响。')
    if config.metadata.get('sample', False):
        warnings.append('当前使用样例数据；样例收益不可作策略结论。')
    warnings.append('动态策略仅使用已有ETF价格特征评分，不包含行业或全市场个股广度选股。')
    dates = pd.to_datetime(data['date'])
    metadata = _metadata(config) | {
        'source': config.metadata.get('source', config.data.source),
        'sample': config.metadata.get('sample', False),
        'adjustment': config.data.adjustment,
        'data_range': {'start': dates.min().date().isoformat() if len(dates) else None,
                       'end': dates.max().date().isoformat() if len(dates) else None},
        'costs': asdict(config.costs),
        'config': asdict(config),
        'candidate_symbols': candidates,
        'ranking_parameters': rank_params,
        'data_coverage': coverage,
        'warnings': warnings,
    }
    results = {}
    rows = []
    fixed_equity = None
    for name, strategy in strategies.items():
        result = _engine(config).run(data, strategy)
        metrics = evaluate(result, benchmark_equity=fixed_equity)
        if name == 'fixed_asset' and benchmark_valid:
            fixed_equity = result.equity
        effective_params = ({'symbol': strategy.symbol} if name == 'fixed_asset' else
                            {'candidate_symbols': candidates, **rank_params})
        report_metadata = metadata | {'strategy': {'name': name, 'parameters': effective_params}}
        paths = write_report(result, metrics, out / name, metadata=report_metadata)
        events_path = out / name / 'events.csv'
        pd.DataFrame(result.events, columns=['as_of', 'index_level', 'index_return_1d', 'triggered', 'declining_count', 'warning']).to_csv(events_path, index=False)
        summary = json.loads(paths.summary.read_text(encoding='utf-8'))
        warnings.extend(warning for warning in summary['warnings'] if warning not in warnings)
        results[name] = {'metrics': asdict(metrics), 'events': getattr(result, 'events', []),
                         'warnings': summary['warnings'], 'files': {p.name: f'{name}/{p.name}' for p in (*paths, events_path)}}
        rows.append({'strategy': name, **asdict(metrics)})
    with (out / 'comparison.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    payload = {'metadata': metadata, 'strategies': results, 'warnings': warnings,
               'files': ['index.html', 'comparison.csv', 'comparison.json']}
    (out / 'comparison.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    _write_html(payload, out)
    return payload


def _write_html(payload: dict, out: Path) -> None:
    meta = payload['metadata']
    settings = meta['config']['backtest']
    period = settings['holding_period_days']
    timing = ('D收盘信号 → D+1开盘买 → D+2开盘卖' if period == 1 else
              f'D收盘信号 → D+1开盘买 → D+{period + 1}开盘卖（持有{period}个交易日）')
    labels = {'fixed_asset': '固定ETF', 'cross_sectional_rank': '动态ETF评分'}
    table_rows, sections = [], []
    for name, result in payload['strategies'].items():
        metrics = result['metrics']
        pct = lambda key: '—' if metrics[key] is None else f'{metrics[key]:.2%}'
        table_rows.append(f'<tr><th>{labels[name]}</th><td>{pct("cumulative_return")}</td><td>{pct("win_rate")}</td><td>{pct("max_drawdown")}</td><td>{metrics["trade_count"]}</td><td>{pct("excess_return")}</td></tr>')
        image = base64.b64encode((out / name / 'report.png').read_bytes()).decode('ascii')
        sections.append(f'<section><h2>{labels[name]}</h2><p><a href="{name}/trades.csv">逐笔交易CSV</a> · <a href="{name}/equity.csv">每日净值CSV</a> · <a href="{name}/events.csv">每日触发审计CSV</a> · <a href="{name}/summary.json">完整指标JSON</a> · <a href="{name}/report.png">report.png</a></p><img alt="{labels[name]}净值与回撤" src="data:image/png;base64,{image}"></section>')
    warning_html = ''.join(f'<li>{escape(str(warning))}</li>' for warning in payload['warnings'])
    config_html = escape(json.dumps(meta, ensure_ascii=False, indent=2, default=str))
    identity = '样例数据' if meta['sample'] else '研究数据（数据身份与来源见下方配置）'
    html = f'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>A股ETF策略比较 · 仅供研究</title>
<style>body{{font:16px/1.7 system-ui,sans-serif;max-width:1100px;margin:auto;padding:28px;color:#162238;background:#f5f7fb}}h1{{font-size:30px}}section,.card{{background:white;padding:24px;border-radius:12px;margin:20px 0}}.notice{{border-left:5px solid #d78d1a;padding:16px;background:#fff4dc}}table{{border-collapse:collapse;width:100%}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #dae1ec}}img{{width:100%;height:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}}a{{color:#1859ba}}.scroll{{overflow-x:auto}}</style>
<h1>A股ETF策略比较</h1><p>仅供研究 · {identity}</p>
<div class="notice"><strong>{escape(timing)}</strong><br>交易日按输入行情日历计算；不是同日尾盘模型。停牌、涨跌停或样本结束可能导致未成交或退出推迟。样例收益不可作策略结论。</div>
<p>样本：{escape(str(meta['data_range']['start']))} 至 {escape(str(meta['data_range']['end']))} · 来源：{escape(str(meta['source']))}</p>
<div class="card"><h2>同输入、同触发、同成本比较</h2><p>固定ETF是比较基准；动态策略仅使用已有ETF价格特征评分。固定ETF不计算相对自身的超额收益。特征窗口不足时动态策略保持现金。</p>
<div class="scroll"><table><thead><tr><th>策略</th><th>累计收益</th><th>胜率</th><th>最大回撤</th><th>交易次数</th><th>相对固定ETF超额收益</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<p>收益已计入配置的佣金、最低佣金、印花税及滑点。印花税依统一配置收取，ETF研究应将其设为0。胜率以已平仓交易计；完整风险指标见JSON。</p><a href="comparison.csv">下载比较CSV</a> · <a href="comparison.json">下载比较JSON</a></div>
<section><h2>数据与执行提示</h2><ul>{warning_html}</ul></section>
{''.join(sections)}<section><h2>配置、样本身份与成本</h2><pre>{config_html}</pre></section></html>'''
    (out / 'index.html').write_text(html, encoding='utf-8')
