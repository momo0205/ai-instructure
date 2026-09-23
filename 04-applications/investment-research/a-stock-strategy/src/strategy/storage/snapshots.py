"""冻结数据、完整 Python 源码及请求，保存回测结果。"""
from pathlib import Path
import hashlib
import json
import shutil
from strategy.market_data.repository import verify_manifests


def freeze_inputs(root, request, output_dir):
    """复制输入并核验清单，返回快照目录与每个冻结文件的 SHA-256。"""
    output = Path(output_dir)
    snapshot = output/'snapshot'
    snapshot.mkdir(parents=True,exist_ok=True)
    source = Path(root)/'data'/request['dataset_id']
    hashes = {}
    files = [(source/f,f) for f in ('market.csv','breadth.csv','manifest.json','market_manifest.json') if (source/f).is_file()]
    frozen_code = Path(root)/'src'/'strategy'
    package = frozen_code if frozen_code.is_dir() else Path(__file__).resolve().parents[1]
    files += [(p,'code/'+str(p.relative_to(package))) for p in package.rglob('*.py')]
    for src,relative in files:
        destination = snapshot/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,destination)
        hashes[relative] = hashlib.sha256(destination.read_bytes()).hexdigest()
    encoded = json.dumps(request,ensure_ascii=False,sort_keys=True,allow_nan=False)
    verify_manifests(snapshot)
    (snapshot/'request.json').write_text(encoded)
    hashes['request.json'] = hashlib.sha256(encoded.encode()).hexdigest()
    return snapshot, hashes


def write_result(output_dir, payload):
    """统一 JSON 值后写入结果，返回与磁盘内容一致的响应。"""
    payload = json.loads(json.dumps(payload,default=str,ensure_ascii=False,allow_nan=False))
    (Path(output_dir)/'result.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False))
    return payload
