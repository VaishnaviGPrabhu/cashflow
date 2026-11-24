import pandas as pd
def build_forecast(cash,revenue_assumptions,recurring_expenses,payroll,hiring_plan=None,months=6):
    ra=revenue_assumptions.copy();ra['month']=pd.to_datetime(ra.month).dt.to_period('M').astype(str);base=float(recurring_expenses.monthly_amount.sum())+float(payroll.monthly_salary.sum());hp={}
    if hiring_plan is not None and len(hiring_plan):
        h=hiring_plan.copy();h['month']=pd.to_datetime(h.month).dt.to_period('M').astype(str);hp=h.groupby('month').apply(lambda x:float((x['count']*x['monthly_salary']).sum()),include_groups=False).to_dict()
    rows=[];opening=cash
    for _,r in ra.head(months).iterrows():
        exp=base+hp.get(r['month'],0);rev=float(r.expected_revenue);net=rev-exp;closing=opening+net
        rows.append({'month':r['month'],'opening_cash':round(opening,2),'revenue':round(rev,2),'expenses':round(exp,2),'net_cash_flow':round(net,2),'closing_cash':round(closing,2),'monthly_burn':round(max(exp-rev,0),2)});opening=closing
    return pd.DataFrame(rows)
def forecast_runway(df):
    if df.empty:return None
    neg=df.index[df.closing_cash<=0]
    if len(neg):return float(neg[0])
    b=float(df.monthly_burn.mean());return None if b<=0 else round(float(df.iloc[0].opening_cash)/b,4)
