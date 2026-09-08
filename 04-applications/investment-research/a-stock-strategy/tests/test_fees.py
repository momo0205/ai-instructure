from datetime import date

import pytest

from strategy.fees import FeeRules, FEES_VERSION, STOCK_SUPPORTED_FROM


def test_stock_date_rates_and_sides():
    fees=FeeRules(.0003,5,.02)
    before=fees.calculate(10000,date(2023,8,27),'stock','sell')
    after=fees.calculate(10000,date(2023,8,28),'stock','sell')
    buy=fees.calculate(10000,date(2023,8,28),'stock','buy')
    assert (before.commission,before.stamp_duty,before.transfer_fee)==(5,10,.1)
    assert (after.commission,after.stamp_duty,after.transfer_fee)==(5,5,.1)
    assert buy.total == pytest.approx(5.1)
    assert STOCK_SUPPORTED_FROM == date(2022,7,1)
    assert fees.metadata()['version']==FEES_VERSION


def test_etf_and_legacy_costs():
    fees=FeeRules(.001,5,.02)
    assert fees.calculate(10000,date(2020,1,1),'etf','sell').total == 10
    assert fees.calculate(10000,date(2020,1,1),None,'sell').total == 210
    assert fees.quantity(10000,10,date(2020,1,1),None,0)==pytest.approx(9995/10.01)


@pytest.mark.parametrize('cash,rate,minimum', [(10005,.0003,5),(10005,.01,5),(10000,0,0),(1,.0003,5)])
def test_budget_reuses_actual_fees(cash,rate,minimum):
    fees=FeeRules(rate,minimum,0)
    day=date(2025,1,1)
    qty=fees.quantity(cash,10,day,'stock',0)
    assert qty % 100 == 0
    assert qty*10+fees.calculate(qty*10,day,'stock','buy').total <= cash
    assert (qty+100)*10+fees.calculate((qty+100)*10,day,'stock','buy').total > cash


def test_rule_validation():
    fees=FeeRules(.0003,5,0)
    with pytest.raises(ValueError,match='2022-07-01'):
        fees.calculate(1000,date(2022,6,30),'stock','buy')
    with pytest.raises(ValueError,match='instrument'):
        fees.calculate(1000,date(2025,1,1),'other','buy')
    with pytest.raises(ValueError,match='side'):
        fees.calculate(1000,date(2025,1,1),'stock','other')
