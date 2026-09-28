from pathlib import Path
import time
import shutil
import json
import pytest
from test_compositions import project, request
from strategy.application.jobs import JobManager
from strategy.application.direct_inputs import submit_selection

def wait(jobs,key):
 for _ in range(300):
  row=jobs.get(key)
  if row['status'] not in ('queued','running'):return row
  time.sleep(.03)
 raise AssertionError(row)

def test_direct_selection_freezes_without_global_dataset_and_replays(project,tmp_path):
 jobs=JobManager(project,tmp_path/'workbench')
 try:
  payload={'selection':request(),'request':{'strategy_id':'price_momentum','parameters':{'candidate_symbols':['510300.SH','159915.SZ'],'lookback':2,'minimum_momentum':-1}}}
  before=sorted(p.name for p in (project/'data').iterdir())
  first=wait(jobs,submit_selection(jobs,payload)['id']);assert first['status']=='succeeded',first
  assert first['request']['snapshot_job_id']==first['id']
  assert sorted(p.name for p in (project/'data').iterdir())==before
  assert len(first['result']['metadata']['input_selection']['members'])==2
  shutil.rmtree(project/'data/managed_a')
  second=wait(jobs,jobs.submit(first['request']|{'holding_period_days':3})['id'])
  assert second['status']=='succeeded',second
  assert second['request']['snapshot_job_id']==second['id']
  manifest=json.loads((jobs.state_dir/'runs'/second['id']/'snapshot/market_manifest.json').read_text())
  assert 'market_manifest.json' in manifest['source_manifest_contents']['managed_a']
  assert 'source_manifest' not in manifest['symbol_sources']['510300.SH']
 finally:jobs.close()

def test_selection_must_match_strategy_symbols(project,tmp_path):
 jobs=JobManager(project,tmp_path/'workbench')
 try:
  with pytest.raises(ValueError):submit_selection(jobs,{'selection':request(),'request':{'strategy_id':'fixed_asset','parameters':{'symbol':'510300.SH'}}})
  assert jobs.list()==[]
 finally:jobs.close()

def test_direct_input_supports_studies_and_single_asset(project,tmp_path):
 from strategy.application.studies import StudyManager
 jobs=JobManager(project,tmp_path/'workbench');studies=StudyManager(jobs)
 try:
  base=wait(jobs,submit_selection(jobs,{'selection':{'base_dataset_id':'real','members':[{'dataset_id':'managed_a','symbol':'510300.SH'}]},'request':{'strategy_id':'fixed_asset','parameters':{'symbol':'510300.SH'}}})['id'])
  assert base['status']=='succeeded'
  batch=studies.submit({'base_job_id':base['id'],'holding_periods':[1,3],'validation_start':'2024-03-01'})
  for _ in range(300):
   group=studies.get(batch['id'])
   if group['status'] not in ('queued','selecting','validating'):break
   time.sleep(.03)
  assert group['status']=='completed',group
 finally:studies.close();jobs.close()
