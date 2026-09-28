"""独立解释器入口：仅计算固定的因果价格表达式，不执行订单或任意用户公式。"""
import json
from pathlib import Path
import sys


def main(folder):
    import numpy as np
    import pandas as pd
    import qlib
    from qlib.data import D

    root = Path(folder).resolve()
    request = json.loads((root/'request.json').read_text())
    lookback = request['lookback']
    if type(lookback) is not int or not 1 <= lookback <= 252:
        raise ValueError('invalid lookback')
    if qlib.__version__ != '0.9.7':
        raise ValueError('unsupported Qlib version')
    frame = pd.read_csv(root/'input.csv', dtype={'symbol': str})
    if frame.duplicated(['date', 'symbol']).any():
        raise ValueError('duplicate input bars')
    dates = sorted(frame.date.unique())
    provider = root/'provider'
    for name in ('calendars', 'features', 'instruments'):
        (provider/name).mkdir(parents=True, exist_ok=True)
    (provider/'calendars/day.txt').write_text('\n'.join(dates)+'\n')
    instruments = []
    for symbol in request['symbols']:
        # 证券代码已经由工作台验证；此处仍限制路径字符，避免输入成为目录路径。
        import re
        if not re.fullmatch(r'\d{6}\.(SH|SZ)', symbol):
            raise ValueError('invalid instrument')
        code, exchange = symbol.split('.')
        instrument = exchange.lower()+code
        directory = provider/'features'/instrument
        directory.mkdir(exist_ok=True)
        rows = frame[frame.symbol==symbol].set_index('date').reindex(dates)
        # 不前向填充缺口；只建立 close 字段，不伪造企业行动 factor。
        np.r_[0, rows.close.to_numpy()].astype('<f4').tofile(directory/'close.day.bin')
        instruments.append(f'{instrument.upper()}\t{dates[0]}\t{dates[-1]}')
    (provider/'instruments/all.txt').write_text('\n'.join(instruments)+'\n')
    qlib.init(provider_uri=str(provider), region='cn', kernels=1,
              expression_cache=None, dataset_cache=None,
              exp_manager={'class':'MLflowExpManager','module_path':'qlib.workflow.expm',
                           'kwargs':{'uri':(root/'unused-mlruns').as_uri(),'default_exp_name':'factor-only'}})
    expression = f'$close/Ref($close, {lookback})-1'
    mapping = {s.split('.')[1]+s.split('.')[0]:s for s in request['symbols']}
    features = D.features(list(mapping), [expression], dates[0], dates[-1])
    rows = []
    for (instrument, day), row in features.iterrows():
        value = float(row.iloc[0])
        rows.append({'date':day.date().isoformat(),'symbol':mapping[instrument],
                     'score':value if np.isfinite(value) else None})
    (root/'output.json').write_text(json.dumps({'version':qlib.__version__,
        'expression':expression,'rows':rows},allow_nan=False))


if __name__ == '__main__':
    main(sys.argv[1])
