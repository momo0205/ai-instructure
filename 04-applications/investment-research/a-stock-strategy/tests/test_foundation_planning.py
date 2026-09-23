"""累计覆盖应复用历史，仅下载真正缺少的依赖日期。"""
import hashlib
import json
from pathlib import Path
import pandas as pd
import pytest
from strategy.application import foundation_planning as planning


def write_part(folder,dates,kind):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if kind=='index':
        frame=pd.DataFrame([dict(date=d,symbol='000001.SH',open=100,high=100,low=100,close=100,volume=1,amount=1,is_suspended=False,limit_up=False,limit_down=False) for d in dates])
        filename,name,field='market.csv','market_manifest.json','market_sha256'
        manifest=dict(source='tencent.newfqkline',adjustment='qfq')
    else:
        frame=pd.DataFrame([dict(date=d,declining_count=4000,total_count=5000,source='tushare.daily',sh_count=2000,sz_count=2700,bj_count=300) for d in dates],columns=['date','declining_count','total_count','source','sh_count','sz_count','bj_count'])
        filename,name,field='breadth.csv','manifest.json','breadth_sha256'
        manifest=dict(source='tushare.daily',universe='SH_SZ_BJ',coverage_dates=dates,empty_dates=[])
    raw=folder/'raw';raw.mkdir(exist_ok=True)
    keys=['response.json'] if kind=='index' else dates
    for key in keys:(raw/(key if kind=='index' else key+'.csv')).write_text('{}' if kind=='index' else 'trade_date,ts_code,pct_chg\n')
    manifest.update(raw_dir=str(raw.resolve()),raw_sha256={key:hashlib.sha256((raw/(key if kind=='index' else key+'.csv')).read_bytes()).hexdigest() for key in keys})
    frame.to_csv(folder/filename,index=False)
    manifest[field]=hashlib.sha256((folder/filename).read_bytes()).hexdigest()
    (folder/name).write_text(json.dumps(manifest))


def seed(root,dates):
    for kind in ('index','breadth'):write_part(root/'data/real',dates,kind)


def test_fully_covered_update_never_calls_provider(tmp_path):
    seed(tmp_path,['2026-01-05','2026-01-06'])
    def no_network(*args,**kwargs):raise AssertionError('unnecessary download')
    result=planning.update_missing(tmp_path,'abcd','2026-01-05','2026-01-06',market_downloader=no_network,breadth_downloader=no_network)
    assert result.startswith('foundation_')
    assert pd.read_csv(tmp_path/'data'/result/'market.csv').shape[0]==2


def test_single_missing_day_downloads_once_and_keeps_old_data(tmp_path):
    dates=['2026-01-05','2026-01-06','2026-01-08','2026-01-09']
    seed(tmp_path,dates);before=(tmp_path/'data/real/market.csv').read_bytes();calls=[]
    def provider(kind):
        def download(start,end,output,**kwargs):
            calls.append((kind,start,end));write_part(output,[start],kind)
        return download
    result=planning.update_missing(tmp_path,'abcd','2026-01-05','2026-01-09',market_downloader=provider('index'),breadth_downloader=provider('breadth'))
    assert sorted(calls)==[('breadth','2026-01-07','2026-01-07'),('index','2026-01-07','2026-01-07')]
    assert len(pd.read_csv(tmp_path/'data'/result/'breadth.csv'))==5
    assert (tmp_path/'data/real/market.csv').read_bytes()==before
    from strategy.market_data.coverage import CoverageIndex
    assert not CoverageIndex(tmp_path).plan('2026-01-05','2026-01-09')['breadth_missing']


def test_failure_never_publishes_partial_foundation(tmp_path):
    seed(tmp_path,['2026-01-05','2026-01-06'])
    def fail(*args,**kwargs):raise ValueError('offline')
    with pytest.raises(ValueError):planning.update_missing(tmp_path,'abcd','2026-01-05','2026-01-09',breadth_downloader=fail)
    assert not list((tmp_path/'data').glob('foundation_*'))


def test_preview_reports_reuse_and_exact_gaps(tmp_path):
    seed(tmp_path,['2026-01-05','2026-01-06'])
    result=planning.preview_update(tmp_path,dict(start='2026-01-05',end='2026-01-07'))
    assert result['reused_index_days']==2
    assert result['breadth_missing']==[dict(start='2026-01-07',end='2026-01-07',days=1)]
    with pytest.raises(ValueError):planning.preview_update(tmp_path,dict(start='2026-01-05',end='2999-01-01'))
