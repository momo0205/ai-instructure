from strategy.validation import UserError
import json
import shutil
import time
from pathlib import Path

import pandas as pd
import pytest
from strategy import workbench

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_excludes_index_and_unknown_stock_from_backtest(tmp_path):
    folder = tmp_path/'data'/'mvp_sample'
    shutil.copytree(ROOT/'data'/'mvp_sample', folder)
    frame = pd.read_csv(folder/'market.csv')
    stock = frame[frame.symbol == '588000.SH'].assign(symbol='002015.SZ')
    pd.concat([frame, stock]).to_csv(folder/'market.csv', index=False)
    instruments = {x['symbol']: x for x in workbench.datasets(tmp_path)[0]['instruments']}
    assert instruments['588000.SH']['backtest_supported']
    assert not instruments['002015.SZ']['backtest_supported']
    assert not instruments['000001.SH']['backtest_supported']
    with pytest.raises(ValueError, match='回测'):
        workbench.validate_request(tmp_path, {'parameters': {'symbol': '002015.SZ'}})


def test_wrong_exchange_rejected():
    from strategy.instruments import validate_symbol
    with pytest.raises(ValueError, match='SZ'):
        validate_symbol('002015.SH')


@pytest.mark.parametrize('memory_tasks', [False, True])
def test_download_publishes_version_without_mutating_base(tmp_path, memory_tasks):
    from test_task_repository import MemoryTaskRepository
    from strategy.instruments import DownloadManager
    folder = tmp_path/'data'/'real'
    shutil.copytree(ROOT/'data'/'mvp_sample', folder)
    (folder/'market_manifest.json').write_text(json.dumps({'adjustment':'none','raw_dir':'data/real/market_raw/old','raw_sha256':{'old.json':'old'}}))
    original = (folder/'market.csv').read_bytes()
    frame = pd.read_csv(folder/'market.csv')
    start, end = frame.date.min(), frame.date.max()

    def downloader(start, end, output_dir, symbols, adjustment):
        source = frame[frame.symbol.isin(['000001.SH', '588000.SH'])].copy()
        source.loc[source.symbol == '588000.SH', 'symbol'] = symbols[0]
        source.to_csv(Path(output_dir)/'market.csv', index=False)
        raw = Path(output_dir)/'market_raw'/'test'
        raw.mkdir(parents=True)
        (raw/'response.json').write_text('{}')
        (Path(output_dir)/'market_manifest.json').write_text(json.dumps({'source':'test','adjustment':adjustment,'raw_dir':str(raw)}))

    manager = DownloadManager(tmp_path, tmp_path/'state', downloader=downloader,
                              resolver=lambda symbol: {'symbol':symbol,'name':'协鑫能科','kind':'stock'},
                              task_repository=MemoryTaskRepository('dataset_id') if memory_tasks else None)
    try:
        task = manager.submit({'symbol':'002015.SZ','start':start,'end':end})
        for _ in range(200):
            task = manager.list()[0]
            if task['status'] not in ('queued','running'):
                break
            time.sleep(.01)
        assert task['status'] == 'succeeded', task
        if memory_tasks:
            assert not list((tmp_path/'state').rglob('*.sqlite3'))
        assert (folder/'market.csv').read_bytes() == original
        dataset = next(x for x in workbench.datasets(tmp_path) if x['id'] == task['dataset_id'])
        assert '002015.SZ' in dataset['symbols']
        published = tmp_path/'data'/task['dataset_id']
        manifest = json.loads((published/'market_manifest.json').read_text())
        inner = json.loads((published/'download'/'market_manifest.json').read_text())
        assert manifest['download']['raw_dir'] == inner['raw_dir']
        assert (published/inner['raw_dir']/'response.json').is_file()
        assert 'raw_dir' not in manifest and 'raw_sha256' not in manifest
        assert manifest['parent_provenance']['raw_dir'] == str((tmp_path/'data/real/market_raw/old').resolve())
        assert manifest['parent_provenance']['raw_dir_base'] == 'absolute'
        assert next(x for x in dataset['instruments'] if x['symbol']=='002015.SZ')['backtest_supported']
        from strategy.jobs import JobManager
        jobs = JobManager(tmp_path, tmp_path/'jobs')
        try:
            assert jobs.submit({'dataset_id':task['dataset_id']})['status'] == 'queued'
        finally:
            jobs.close()
    finally:
        manager.close()


def test_failed_download_can_retry_and_does_not_publish(tmp_path):
    from strategy.instruments import DownloadManager
    folder = tmp_path/'data'/'real'
    shutil.copytree(ROOT/'data'/'mvp_sample', folder)
    manager = DownloadManager(tmp_path, tmp_path/'state', resolver=lambda _: (_ for _ in ()).throw(UserError('SYMBOL_NOT_CONFIRMED', '代码不存在')))
    try:
        request = {'symbol':'002015.SZ','start':'2024-02-01','end':'2024-02-02'}
        for _ in range(2):
            manager.submit(request)
            for _ in range(200):
                if manager.list()[0]['status']=='failed':
                    break
                time.sleep(.01)
            assert manager.list()[0]['error']=='代码不存在'
            assert manager.list()[0]['diagnostic']['code']=='SYMBOL_NOT_CONFIRMED'
        assert len(manager.list())==2
        assert not list((tmp_path/'data').glob('managed_*'))
    finally:
        manager.close()


def test_download_restart_interrupts_unfinished(tmp_path):
    import sqlite3
    from strategy.instruments import DownloadManager
    manager = DownloadManager(tmp_path, tmp_path/'state')
    manager.close()
    with sqlite3.connect(tmp_path/'state'/'downloads.sqlite3') as db:
        db.execute("INSERT INTO downloads VALUES ('pending','running','{}','now',NULL,NULL)")
    manager = DownloadManager(tmp_path, tmp_path/'state')
    try:
        assert manager.list()[0]['status']=='interrupted'
    finally:
        manager.close()


def test_instrument_and_download_routes(tmp_path):
    from strategy.web import dispatch
    from strategy.instruments import DownloadManager
    downloads = DownloadManager(tmp_path, tmp_path/'state')
    try:
        assert dispatch('GET','/api/instruments',None,ROOT,None,downloads)[0]==200
        assert dispatch('GET','/api/downloads',None,ROOT,None,downloads)==(200,[])
        assert dispatch('POST','/api/downloads',{'symbol':'002015.SH','start':'2024-01-01','end':'2024-01-02'},ROOT,None,downloads)[0]==400
    finally:
        downloads.close()


def test_managed_dataset_name_and_per_symbol_sources(tmp_path):
    folder = tmp_path/'data'/'managed_test'
    shutil.copytree(ROOT/'data'/'mvp_sample', folder)
    (folder/'market_manifest.json').write_text(json.dumps({'instruments':{'588000.SH':{'name':'科创50ETF'}},'updated_symbol':'588000.SH'}))
    dataset = workbench.datasets(tmp_path)[0]
    assert '588000.SH' in dataset['name']


def test_resolver_requires_matching_quote_code(monkeypatch):
    from strategy import instruments
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return 'v_sz002015="51~协鑫能科~002015~10";'.encode('gbk')
    monkeypatch.setattr(instruments, 'urlopen', lambda *args, **kwargs: Response())
    assert instruments.resolve_instrument('002015.SZ') == {'symbol':'002015.SZ','name':'协鑫能科','kind':'stock'}
    with pytest.raises(ValueError, match='未确认'):
        instruments.resolve_instrument('002016.SZ')


def test_partial_etf_refresh_replaces_whole_symbol_history(tmp_path):
    from strategy.instruments import DownloadManager
    folder = tmp_path/'data'/'real'
    shutil.copytree(ROOT/'data'/'mvp_sample', folder)
    (folder/'market_manifest.json').write_text('{"adjustment":"none"}')
    frame = pd.read_csv(folder/'market.csv')
    dates = sorted(frame.date.unique())
    first, last = dates[2], dates[-2]
    def downloader(start, end, output_dir, symbols, adjustment):
        incoming = frame[frame.symbol.isin(['000001.SH', '588000.SH']) & frame.date.between(start,end)]
        incoming.to_csv(Path(output_dir)/'market.csv',index=False)
        (Path(output_dir)/'market_manifest.json').write_text('{}')
    manager = DownloadManager(tmp_path, tmp_path/'state', downloader=downloader,
                              resolver=lambda symbol: {'symbol':symbol,'name':'科创50ETF','kind':'etf'})
    try:
        task = manager.submit({'symbol':'588000.SH','start':first,'end':last})
        for _ in range(200):
            task = manager.list()[0]
            if task['status'] not in ('queued','running'):
                break
            time.sleep(.01)
        assert task['status']=='succeeded', task
        dataset = next(x for x in workbench.datasets(tmp_path) if x['id']==task['dataset_id'])
        symbol = next(x for x in dataset['instruments'] if x['symbol']=='588000.SH')
        assert (symbol['start'],symbol['end'])==(first,last)
        with pytest.raises(ValueError,match='coverage'):
            workbench.validate_request(tmp_path,{'dataset_id':task['dataset_id']})
        assert workbench.validate_request(tmp_path,{'dataset_id':task['dataset_id'],'start':first,'end':last})
        manifest = json.loads((tmp_path/'data'/task['dataset_id']/'market_manifest.json').read_text())
        assert manifest['symbol_sources']['510300.SH']['dataset']=='real'
    finally:
        manager.close()


@pytest.mark.parametrize('configuration, expected', [(None,None), ('unknown',None), ('none','none')])
def test_missing_manifest_requires_explicit_adjustment(tmp_path, configuration, expected):
    from strategy.instruments import DownloadManager
    folder = tmp_path/'data'/'real'
    shutil.copytree(ROOT/'data'/'mvp_sample',folder)
    if configuration:
        (tmp_path/'configs').mkdir()
        (tmp_path/'configs'/'real_breadth.toml').write_text(f'[data]\nadjustment = "{configuration}"\n')
    seen = []
    def downloader(*args, **kwargs):
        seen.append(kwargs['adjustment'])
        raise ValueError('download reached')
    manager = DownloadManager(tmp_path,tmp_path/'state',downloader=downloader,resolver=lambda symbol:{'symbol':symbol})
    try:
        message = 'download reached' if expected else '复权方式未知'
        with pytest.raises(ValueError,match=message):
            manager._publish('test',{'symbol':'002015.SZ','start':'2024-02-01','end':'2024-02-02'})
        assert seen == ([expected] if expected else [])
    finally:
        manager.close()
