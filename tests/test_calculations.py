from core.calculations import *
def test_runway():assert abs(calculate_runway(250000,36500)-6.8493)<.001
def test_zero():assert calculate_runway(250000,0) is None
def test_variance():assert variance(120,100)['percent']==.2
def test_scenario():assert scenario_cashflow(250000,20000,50000,3).iloc[-1].closing_cash==160000
def test_hiring():assert hiring_impact(250000,36500,2,12000)['new_burn']==60500
