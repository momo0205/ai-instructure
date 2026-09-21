"""证券选择直接冻结成任务输入，不向全局行情目录发布组合版本。"""
from pathlib import Path
import tempfile
import json
from strategy.application.compositions import CompositionService
from strategy.strategies.registry import get_strategy_definition
from strategy.market_data.repository import datasets
from strategy.validation import UserError


def submit_selection(jobs, payload):
    if not isinstance(payload,dict) or set(payload)!={'request','selection'} or not isinstance(payload['request'],dict):
        raise UserError('INVALID_REQUEST','请提供回测参数和证券来源选择')
    request=payload['request'];selection=payload['selection']
    if 'snapshot_job_id' in request:
        raise UserError('INVALID_REQUEST','原任务快照与新的来源选择不能同时使用')
    definition=get_strategy_definition(request.get('strategy_id','fixed_asset'))
    parameters=definition.normalize_parameters(request.get('parameters',{}))
    # 复用组合的冻结和兼容性检查；临时目录结束时清理，任务已持有自己的副本。
    with tempfile.TemporaryDirectory(prefix='research-input-') as folder:
        root=Path(folder);stage=root/'data'/'managed_input';stage.mkdir(parents=True)
        CompositionService(jobs.root)._prepare(selection,stage,minimum_members=1)
        if set(definition.symbols(parameters))!={m['symbol'] for m in selection['members']}:
            raise UserError('INVALID_REQUEST','策略标的必须与本次证券来源选择一致')
        # 临时sources目录不会随任务长期存在；把清单原文内嵌到顶层审计文件。
        # 原始下载响应仍是明确的外部依赖，不伪称已复制供应商原始响应。
        manifest_path=stage/'market_manifest.json'
        manifest=json.loads(manifest_path.read_text())
        manifest['source_manifest_contents']={folder.name:{p.name:p.read_text() for p in folder.glob('*manifest.json')} for folder in (stage/'sources').iterdir()}
        for item in manifest['symbol_sources'].values():
            item.pop('source_manifest',None)
            item['source_manifest_key']=item['dataset']
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        normalized=request|{'dataset_id':'managed_input','parameters':parameters}
        return jobs._submit(normalized,root,snapshot_input=True)


def input_dataset(jobs, identifier):
    job=jobs.get(identifier)
    root=jobs.state_dir/'runs'/identifier/'input_project'
    entry=next(d for d in datasets(root) if d['id']==job['request']['dataset_id'])
    return entry|{'name':f"原任务冻结输入 · {identifier[:8]}"}
