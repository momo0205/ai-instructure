from strategy.application.diagnostics import diagnostic, encode_error, task_view, result_diagnostics, exception_diagnostic


def test_task_diagnostic_survives_storage_and_old_text():
    item = diagnostic('DOWNLOAD_FAILED')
    viewed = task_view({'status':'failed','error':encode_error(item)}, 'download')
    assert viewed['error'] == item['message']
    assert viewed['diagnostic'] == item
    assert task_view({'status':'failed','error':'旧任务失败'}, 'download')['diagnostic']['code'] == 'DOWNLOAD_FAILED'


def test_unknown_exception_does_not_expose_secrets():
    item = exception_diagnostic(RuntimeError('token=secret'), 'backtest')
    assert item['code'] == 'BACKTEST_FAILED'
    assert 'secret' not in str(item)


def test_zero_trade_diagnostics_use_execution_evidence():
    result = {'trades':[], 'execution_events':[{'side':'buy','status':'cancelled','reason':'insufficient_cash','cash':100000,'required_cash':150000}]}
    items = result_diagnostics(result)
    assert items[0]['code'] == 'INSUFFICIENT_CASH'
    assert items[0]['context']['count'] == 1
    assert items[0]['context']['minimum_required_cash'] == 150000
    result['execution_events'].append({'side':'buy','status':'filled'})
    assert result_diagnostics(result)[0]['code'] == 'OPEN_POSITION'
    assert result_diagnostics({'trades':[], 'execution_events':[]})[0]['code'] == 'NO_COMPLETED_TRADES'


def test_validation_has_specific_code_and_safe_chinese_detail():
    from strategy.validation import UserError
    item = exception_diagnostic(UserError('DATA_COVERAGE_INCOMPLETE', '所选标的缺少交易日行情'), 'request')
    assert item['code'] == 'DATA_COVERAGE_INCOMPLETE'
    assert item['message'] == '所选标的缺少交易日行情'


def test_http_uses_typed_validation_diagnostic():
    from strategy.interfaces.web.server import dispatch
    from strategy.validation import UserError
    class Manager:
        def submit(self, request):
            raise UserError('DATA_COVERAGE_INCOMPLETE', '所选标的缺少交易日行情')
    status, body = dispatch('POST', '/api/jobs', {}, None, Manager())
    assert status == 400
    assert body['diagnostic']['code'] == 'DATA_COVERAGE_INCOMPLETE'


def test_partial_results_still_expose_cancelled_entries_and_open_position():
    result={'trades':[{}], 'execution_events':[
        {'side':'buy','status':'filled'}, {'side':'sell','status':'filled'},
        {'side':'buy','status':'cancelled','reason':'insufficient_cash'},
        {'side':'buy','status':'filled'}]}
    codes={d['code'] for d in result_diagnostics(result)}
    assert {'OPEN_POSITION','INSUFFICIENT_CASH'} <= codes


def test_trading_blocks_are_explained_even_with_completed_trades():
    items=result_diagnostics({'trades':[{}], 'execution_events':[
        {'side':'buy','status':'cancelled','reason':'limit_up'},
        {'side':'sell','status':'deferred','reason':'suspended'}]})
    item=next(d for d in items if d['code']=='ORDER_BLOCKED')
    assert '涨停' in item['message'] and '停牌' in item['message']
