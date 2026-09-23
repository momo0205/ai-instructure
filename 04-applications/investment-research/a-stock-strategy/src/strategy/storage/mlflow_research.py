"""独立环境中的 MLflow 查询/备注适配器，不向主服务引入 SDK 依赖。"""
import json
import math
from pathlib import Path
import sys

EXPERIMENT_NAME = 'a-stock-workbench'
ANNOTATION_TAG = 'workbench.annotation'


def parameter(run, name):
    value = run.data.params.get(name)
    if value is None:
        return None
    try:
        return json.loads(value)
    except ValueError:
        return value


def query_runs(client):
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        return []
    runs = client.search_runs([experiment.experiment_id],
                              filter_string="attributes.status = 'FINISHED'",
                              order_by=['attributes.start_time DESC'], max_results=200)
    output = []
    for run in runs:
        try:
            annotation = json.loads(run.data.tags.get(ANNOTATION_TAG, '{}'))
            if not isinstance(annotation, dict):
                annotation = {}
        except (TypeError, ValueError):
            annotation = {}
        metrics = {k:v for k,v in run.data.metrics.items() if math.isfinite(v)}
        output.append({
            'job_id': run.data.tags.get('job_id'), 'run_id': run.info.run_id,
            'name': annotation.get('name', ''), 'notes': annotation.get('notes', ''),
            'strategy_version': parameter(run, 'strategy_version'),
            'data_version': parameter(run, 'data_version'),
            'source_snapshot': parameter(run, 'source_snapshot'),
            'metrics': {k.removeprefix('strategy.'):v for k,v in metrics.items() if k.startswith('strategy.')},
            'controls': {
                'buy_hold_return': metrics.get('effectiveness.buy_and_hold.metrics.cumulative_return'),
                'random_median_return': metrics.get('effectiveness.random.median_return'),
                'random_percentile': metrics.get('effectiveness.random.strategy_percentile'),
            },
        })
    return output


def label_run(client, job_id, run_id, annotation):
    run = client.get_run(run_id)
    experiment = client.get_experiment(run.info.experiment_id)
    if run.data.tags.get('job_id') != job_id or experiment.name != EXPERIMENT_NAME or run.info.status != 'FINISHED':
        raise ValueError('实验记录与任务不匹配')
    # 一个 JSON 标签原子保存名称和备注，避免两次独立写入导致部分更新。
    client.set_tag(run_id, ANNOTATION_TAG, json.dumps(annotation, ensure_ascii=False))
    return annotation


if __name__ == '__main__':
    from mlflow import MlflowClient
    root = Path(sys.argv[1]).resolve()
    client = MlflowClient(tracking_uri=f"sqlite:///{root / 'mlflow.sqlite3'}")
    action = sys.argv[2]
    payload = json.load(sys.stdin)
    if action == 'list':
        result = query_runs(client)
    elif action == 'label':
        result = label_run(client, payload['job_id'], payload['run_id'], payload['annotation'])
    else:
        raise ValueError('unsupported research action')
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
