import sys; sys.path.insert(0, '.')
from mira_runner import pull_all_data
import json
data = pull_all_data('600519')
for k, v in data.items():
    if 'error' in v: print(f'{k}: ERROR {v["error"][:80]}')
    else: print(f'{k}: OK {json.dumps(v, ensure_ascii=False)[:120]}')
