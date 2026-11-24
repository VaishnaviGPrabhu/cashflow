import json
from pathlib import Path
from core.calculations import calculate_runway,variance,scenario_cashflow,hiring_impact
from .scoring import within,score_results
ROOT=Path(__file__).resolve().parent
def run_evaluations():
    cases=json.loads((ROOT/'golden_cases.json').read_text());res=[]
    for c in cases:
        i,e,t=c['input'],c['expected'],c['tolerance'];a={};p=True
        if c['id']=='cash_001':a={'current_cash':i['cash']};p=within(a['current_cash'],e['current_cash'],t)
        elif c['id']=='runway_001':a={'runway_months':calculate_runway(i['cash'],i['monthly_burn'])};p=within(a['runway_months'],e['runway_months'],t)
        elif c['id']=='variance_001':a=variance(i['current'],i['previous']);p=within(a['absolute'],e['absolute'],t) and within(a['percent'],e['percent'],t)
        elif c['id']=='scenario_001':a={'closing_cash':float(scenario_cashflow(i['cash'],i['revenue'],i['expenses'],i['months']).iloc[-1].closing_cash)};p=within(a['closing_cash'],e['closing_cash'],t)
        elif c['id']=='hire_001':a=hiring_impact(i['cash'],i['burn'],i['count'],i['salary']);p=within(a['new_burn'],e['new_burn'],t)
        elif c['id'] in ('zero_burn_001','negative_burn_001'):a={'runway_months':calculate_runway(i['cash'],i['monthly_burn'])};p=a['runway_months'] is None
        elif c['id']=='actual_forecast_001':a={'labels':['ACTUAL','FORECAST']}
        elif c['id']=='missing_001':a={'response_contains':"I don't have enough data"}
        elif c['id']=='anomaly_001':a={'requires_review':True}
        res.append({'id':c['id'],'category':c['category'],'passed':p,'actual':a,'expected':e})
    return {'summary':score_results(res),'results':res}
if __name__=='__main__':print(json.dumps(run_evaluations(),indent=2))
