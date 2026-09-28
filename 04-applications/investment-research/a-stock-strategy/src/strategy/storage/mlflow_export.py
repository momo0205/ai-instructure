"""在单独 Python 环境运行的 MLflow 适配器；生产进程无需导入 MLflow。"""
import hashlib
import json
import math
from pathlib import Path
import sys


def flatten(value, prefix=''):
    """稳定展开嵌套结构，数组保留为 JSON 参数；数值指标单独筛选。"""
    for key, item in value.items():
        name = f'{prefix}.{key}' if prefix else key
        if isinstance(item, dict):
            yield from flatten(item, name)
        else:
            yield name, item


def export(state_dir, key):
    from mlflow import MlflowClient
    from mlflow.entities import Metric, Param
    import time
    root = Path(state_dir).resolve()
    folder = root / 'runs' / key
    result = json.loads((folder / 'result.json').read_text())
    client = MlflowClient(tracking_uri=f"sqlite:///{root / 'mlflow.sqlite3'}")
    name = 'a-stock-workbench'
    experiment = client.get_experiment_by_name(name)
    eid = experiment.experiment_id if experiment else client.create_experiment(
        name, artifact_location=(root / 'mlflow-artifacts').as_uri())
    checkpoint = folder / 'mlflow-run.json'
    if checkpoint.exists():
        run_id = json.loads(checkpoint.read_text())['run_id']
    else:
        # 若创建成功后进程尚未落检查点即中断，通过稳定 job 标签找回。
        found = client.search_runs([eid], filter_string=f"tags.job_id = '{key}'", max_results=1)
        run_id = found[0].info.run_id if found else client.create_run(eid, tags={
            'job_id': key, 'strategy_id': result['request']['strategy_id'],
            'mlflow.runName': f"{result['request']['strategy_id']} / {key[:8]}",
        }).info.run_id
        temporary = checkpoint.with_suffix('.tmp')
        temporary.write_text(json.dumps({'run_id': run_id, 'experiment_id': eid}))
        temporary.replace(checkpoint)
    try:
        request = result['request']
        metadata = result.get('metadata', {})
        parameters = dict(flatten(request))
        if metadata.get('study'):
            parameters.update(flatten(metadata['study'], 'study'))
            client.set_tag(run_id, 'study_id', metadata['study']['id'])
            client.set_tag(run_id, 'study_phase', metadata['study']['phase'])
        parameters['strategy_version'] = metadata.get('strategy_version', 'unknown')
        parameters['execution_mode'] = metadata.get('execution_mode', 'unknown')
        hashes = metadata.get('hashes', {})
        for label, entries in (
            ('data_version', {k:v for k,v in hashes.items() if not k.startswith('code/') and k != 'request.json'}),
            ('source_snapshot', {k:v for k,v in hashes.items() if k.startswith('code/')}),
        ):
            parameters[label] = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest() if entries else 'unknown'
        # 不截断参数：超长值让同步明确失败，完整请求仍保留在 result artifact。
        params = [Param(k, json.dumps(v, ensure_ascii=False, sort_keys=True)) for k,v in parameters.items()]
        numerical = dict(flatten(result.get('metrics', {}), 'strategy'))
        numerical.update(flatten(result.get('effectiveness', {}), 'effectiveness'))
        stamp = int(time.time() * 1000)
        metrics = [Metric(k, float(v), stamp, 0) for k,v in numerical.items()
                   if isinstance(v, (int,float)) and not isinstance(v, bool) and math.isfinite(v)]
        client.log_batch(run_id, metrics=metrics, params=params)
        # 仅显式导出结果与审计元数据；不复制环境变量、任意目录或 Git diff。
        client.log_artifact(run_id, str(folder / 'result.json'))
        client.set_terminated(run_id, status='FINISHED')
    except Exception:
        client.set_terminated(run_id, status='FAILED')
        raise
    return {'run_id': run_id, 'experiment_id': eid}


if __name__ == '__main__':
    export(sys.argv[1], sys.argv[2])
