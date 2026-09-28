"""基础更新计划：复用已验证日期，按缺口取数，再冻结完整研究基础。"""
from pathlib import Path
import re
import shutil
from strategy.validation import UserError
from strategy.market_data.coverage import CoverageIndex
from strategy.market_data.tencent import download_market
from strategy.market_data.ingest import download_tushare_daily
from strategy.market_data.foundations import _manifest


def update_missing(root, identifier, start, end, *, token=None, progress=None,
                   market_downloader=None, breadth_downloader=None):
    if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]+',identifier):
        raise UserError('INVALID_REQUEST','基础任务编号不合法')
    index=CoverageIndex(root)
    plan=index.plan(start,end)
    if plan['conflicts']:
        raise UserError('DATA_VALIDATION_FAILED','请求区间存在基础数据冲突，请先核对来源；不会自动覆盖')
    def report(message):
        if progress: progress(dict(stage='planning',message=message))
    report(f"已复用指数 {plan['reused_index_days']} 天、广度 {plan['reused_breadth_days']} 天")
    if not plan['index_missing'] and not plan['breadth_missing']:
        return index.snapshot(start,end,identifier=identifier,reusable=True)
    # 证据目录不改名，避免外部来源引用在快照发布后失效。
    parts=Path(root)/'reports'/'foundation-parts'/identifier
    parts.mkdir(parents=True,exist_ok=False)
    folders=[]
    try:
        # 先取广度：已留存的空工作日可避免对节假日发起无意义的指数请求。
        for number,span in enumerate(plan['breadth_missing']):
            out=parts/f'breadth_{number}'
            report(f"补齐广度 {span['start']} — {span['end']}")
            kwargs=dict(token=token)
            if breadth_downloader is None:kwargs['progress']=progress
            (breadth_downloader or download_tushare_daily)(span['start'],span['end'],out,**kwargs)
            _manifest(out,'manifest.json','breadth_sha256',parts,True)
            folders.append(out)
        index=CoverageIndex(root,extra_folders=folders)
        remaining=index.plan(start,end)
        for number,span in enumerate(remaining['index_missing']):
            out=parts/f'index_{number}'
            report(f"补齐指数 {span['start']} — {span['end']}")
            (market_downloader or download_market)(span['start'],span['end'],out,
                symbols=['000001.SH'],adjustment='qfq',strict_calendar=False)
            _manifest(out,'market_manifest.json','market_sha256',parts)
            folders.append(out)
        # 所有缺口及冲突再次检查；失败不暴露半成品，也不修改原始版本。
        combined=CoverageIndex(root,extra_folders=folders)
        result=combined.snapshot(start,end,identifier=identifier,reusable=True)
        return result
    except Exception:
        shutil.rmtree(parts,ignore_errors=True)
        raise


def preview_update(root, request):
    """规划只读，不索取凭据，也不修改已下载数据。"""
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    if not isinstance(request,dict) or set(request)!={'start','end'}:
        raise UserError('INVALID_REQUEST','覆盖检查需要 start、end')
    try:
        start,end=(date.fromisoformat(request[k]) for k in ('start','end'))
        if start.isoformat()!=request['start'] or end.isoformat()!=request['end']: raise ValueError
        if not start<=end<datetime.now(ZoneInfo('Asia/Shanghai')).date() or (end-start).days>1096: raise ValueError
    except (ValueError,TypeError):
        raise UserError('INVALID_REQUEST','请使用三年以内的历史日期区间，结束日须早于今天') from None
    return CoverageIndex(root).plan(start.isoformat(),end.isoformat())
