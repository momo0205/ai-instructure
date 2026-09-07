import pytest


def test_tencent_parser_uses_amount_column_and_filters_requested_dates():
    from strategy.market_download import parse_bars
    payload={'data':{'sh588000':{'day':[
        ['2023-12-29','1','1.1','1.2','.9','100',{},'3','11',''],
        ['2024-01-02','1','1.1','1.2','.9','100',{},'3','11','']]}}}
    frame=parse_bars(payload,'sh588000','2024-01-01','2024-12-31','none')
    assert len(frame)==1 and frame.iloc[0].amount==110000
    assert frame.iloc[0].volume==10000
    assert frame.iloc[0].symbol=='588000.SH'


def test_tencent_parser_never_silently_calls_unadjusted_data_adjusted():
    from strategy.market_download import parse_bars
    with pytest.raises(ValueError,match='qfq'):
        parse_bars({'data':{'sh588000':{'day':[]}}},'sh588000','2024-01-01','2024-12-31','qfq')


def test_tencent_parser_rejects_conflicting_duplicate_dates():
    from strategy.market_download import parse_bars
    rows=[['2024-01-02','1','1','1','.9','100',{},'3','11'],
          ['2024-01-02','1','1.1','1.2','.9','100',{},'3','12']]
    with pytest.raises(ValueError,match='duplicate'):
        parse_bars({'data':{'sh588000':{'day':rows}}},'sh588000','2024-01-01','2024-12-31','none')
