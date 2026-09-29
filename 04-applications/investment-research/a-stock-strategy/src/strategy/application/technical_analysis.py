"""Read-only analysis of a single verified independent market asset."""
from datetime import date
import math
from pathlib import Path

import pandas as pd

from strategy.indicators import calculate_series, indicator_catalog, normalize_instances
from strategy.market_data.assets import load_asset_market
from strategy.validation import UserError


def _date(value, name):
    if not isinstance(value, str):
        raise UserError('INVALID_REQUEST', f'{name} 应为 YYYY-MM-DD 日期')
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise UserError('INVALID_REQUEST', f'{name} 应为 YYYY-MM-DD 日期') from None
    if parsed.isoformat() != value:
        raise UserError('INVALID_REQUEST', f'{name} 应为 YYYY-MM-DD 日期')
    return parsed


def _finite(value, *, nonnegative=False):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) and (number >= 0 if nonnegative else number > 0) else None


class TechnicalAnalysisService:
    def __init__(self, root):
        self.root = Path(root)

    def sources(self) -> dict:
        """Report healthy independent versions; one bad asset cannot hide peers."""
        sources, warnings = [], []
        for folder in sorted((self.root/'data').glob('asset_*')):
            try:
                manifest, frame = load_asset_market(self.root, folder.name, allow_missing_prices=True)
                symbol = manifest['updated_symbol']
                security = frame[frame.symbol == symbol]
                if security.empty:
                    raise UserError('DATA_VALIDATION_FAILED', '行情版本缺少目标证券')
                metadata = manifest['instruments'][symbol]
                sources.append(dict(id=folder.name, symbol=symbol, name=metadata.get('name', symbol),
                                    source=manifest.get('source', 'unknown'),
                                    adjustment=manifest.get('adjustment', 'unknown'),
                                    start=security.date.min().date().isoformat(),
                                    end=security.date.max().date().isoformat(),
                                    rows=len(security), warnings=manifest.get('warnings', [])))
            except (ValueError, OSError, KeyError, TypeError):
                warnings.append(f'{folder.name}：行情版本不可用，已从技术分析列表略过。')
        return dict(sources=sources, warnings=warnings)

    def analyze(self, request: dict) -> dict:
        if not isinstance(request, dict) or set(request) != {'source_id','symbol','start','end','indicators'}:
            raise UserError('INVALID_REQUEST', '分析请求需要来源、证券、区间和指标实例')
        start, end = _date(request['start'], 'start'), _date(request['end'], 'end')
        if start > end:
            raise UserError('INVALID_REQUEST', '分析开始日期不能晚于结束日期')
        instances = normalize_instances(request['indicators'])
        manifest, frame = load_asset_market(self.root, request['source_id'], allow_missing_prices=True)
        symbol = manifest.get('updated_symbol')
        if not isinstance(symbol, str) or request['symbol'] != symbol:
            raise UserError('INVALID_REQUEST', '所选行情版本与证券代码不匹配')
        security = frame[frame.symbol == symbol].set_index('date')
        if security.empty:
            raise UserError('DATA_VALIDATION_FAILED', '行情版本缺少目标证券')
        index_dates = set(frame.loc[frame.symbol == '000001.SH', 'date'])
        calendar = sorted(set(security.index) | index_dates)
        if len(calendar) > 5000:
            raise UserError('INVALID_REQUEST', '分析输入最多 5,000 个日历位置（含预热）')
        if not any(start <= stamp.date() <= end for stamp in calendar):
            raise UserError('INVALID_REQUEST', '所选区间没有可分析日期')
        aligned = security.reindex(pd.DatetimeIndex(calendar))
        daily = []
        for stamp, row in aligned.iterrows():
            present = stamp in security.index
            item = dict(date=stamp.date().isoformat(),
                        open=_finite(row.get('open')), high=_finite(row.get('high')),
                        low=_finite(row.get('low')), close=_finite(row.get('close')),
                        volume=_finite(row.get('volume'), nonnegative=True),
                        amount=_finite(row.get('amount'), nonnegative=True),
                        status=('suspended_quote' if row.get('is_suspended') is True else 'observed_quote') if present else 'missing_quote',
                        trading_status=('suspended' if row.get('is_suspended') is True else 'unknown') if present else 'no_quote')
            daily.append(item)
        values = calculate_series(daily, instances)
        for position, item in enumerate(daily):
            item['indicators'] = {instance['instance_id']: values[instance['instance_id']][position] for instance in instances}
        selected = [item for item in daily if request['start'] <= item['date'] <= request['end']]
        definitions = {entry['id']: entry for entry in indicator_catalog()}
        output_instances = [dict(instance, name=definitions[instance['id']]['name'],
                                 category=definitions[instance['id']]['category'],
                                 version=definitions[instance['id']]['version'],
                                 outputs=definitions[instance['id']]['outputs'],
                                 panel=definitions[instance['id']]['panel']) for instance in instances]
        metadata = manifest.get('instruments', {}).get(symbol, {})
        warnings = list(manifest.get('warnings') or [])
        if not index_dates:
            warnings.append('没有指数日期参照；交易日历完整性未验证。')
        return dict(request=dict(request, indicators=instances),
                    source=dict(id=request['source_id'], symbol=symbol, name=metadata.get('name', symbol),
                                source=manifest.get('source','unknown'), adjustment=manifest.get('adjustment','unknown'),
                                market_sha256=manifest['market_sha256'],
                                volume_unit=manifest.get('volume_unit','原始单位未声明'),
                                amount_unit=manifest.get('amount_unit','原始单位未声明'),
                                start=security.index.min().date().isoformat(),
                                end=security.index.max().date().isoformat()),
                    calendar=dict(basis='observed_index' if index_dates else 'security_only',
                                  complete=False, positions=len(calendar)),
                    calculation_start=daily[0]['date'], instances=output_instances,
                    rows=selected, warnings=warnings)
