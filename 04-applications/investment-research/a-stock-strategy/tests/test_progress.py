from strategy.application.progress import progress_scope, report_progress


def test_progress_listener_is_scoped():
    events=[]
    report_progress('outside',0,1)
    with progress_scope(lambda **event: events.append(event)):
        report_progress('random',3,100)
    report_progress('outside',0,1)
    assert events==[{'stage':'random','completed':3,'total':100}]


def test_manager_exposes_progress_and_cancel_stops_at_checkpoint(tmp_path,monkeypatch):
    from pathlib import Path
    import threading,time
    from strategy.application.jobs import JobManager
    import strategy.application.jobs as jobs
    entered,release=threading.Event(),threading.Event()
    reached=[]
    def slow(root,request,output):
        report_progress('random',7,100);entered.set();release.wait(3)
        report_progress('random',8,100);reached.append('continued')
        return {'ok':True}
    monkeypatch.setattr(jobs,'execute',slow)
    manager=JobManager(Path(__file__).resolve().parents[1],tmp_path)
    try:
        identifier=manager.submit({})['id'];assert entered.wait(2)
        assert manager.get(identifier)['progress']['completed']==7
        assert manager.list()[0]['progress']['stage']=='random'
        manager.cancel(identifier);release.set()
    finally:
        release.set();manager.close()
    assert not reached
