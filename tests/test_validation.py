import pandas as pd
from core.validators import validate_dataframe
def test_missing():assert any(i.severity=='HIGH' for i in validate_dataframe('transactions',pd.DataFrame({'date':['bad']})))
def test_negative():
 d=pd.DataFrame({'date':['2026-01-01'],'type':['outflow'],'category':['x'],'vendor':['v'],'amount':[-5]});assert any(i.severity=='MEDIUM' for i in validate_dataframe('transactions',d))
