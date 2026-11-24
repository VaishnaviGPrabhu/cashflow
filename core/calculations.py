import numpy as np,pandas as pd
def current_cash(t,starting_cash=250000):
    if t.empty:return round(float(starting_cash),2)
    signed=np.where(t.type.str.lower().eq('inflow'),t.amount,-t.amount);return round(float(starting_cash+signed.sum()),2)
def monthly_flows(t):
    x=t.copy();x['date']=pd.to_datetime(x.date);x['month']=x.date.dt.to_period('M').astype(str)
    x['inflow']=np.where(x.type.str.lower().eq('inflow'),x.amount,0.0);x['outflow']=np.where(x.type.str.lower().eq('outflow'),x.amount,0.0)
    return x.groupby('month',as_index=False)[['inflow','outflow']].sum()
def total_inflows(t):return round(float(t.loc[t.type.str.lower()=='inflow','amount'].sum()),2)
def total_outflows(t):return round(float(t.loc[t.type.str.lower()=='outflow','amount'].sum()),2)
def net_cash_flow(t):return round(total_inflows(t)-total_outflows(t),2)
def monthly_burn(recurring,payroll,transactions=None):
    cost=float(recurring.monthly_amount.sum())+float(payroll.monthly_salary.sum())
    rev=0
    if transactions is not None and len(transactions):
        months=max(pd.to_datetime(transactions.date).dt.to_period('M').nunique(),1)
        rev=float(transactions.loc[transactions.type.str.lower()=='inflow','amount'].sum())/months
    return round(cost-rev,2)
def calculate_runway(cash,burn):return None if burn<=0 else round(float(cash)/float(burn),4)
def variance(current,previous):
    a=round(float(current-previous),2);return {'current':float(current),'previous':float(previous),'absolute':a,'percent':None if previous==0 else round(a/previous,4)}
def scenario_cashflow(cash,revenue,expenses,months=6,revenue_growth_rate=0,expense_growth_rate=0,one_time_expenses=0,payment_delay_months=0,hiring_monthly_cost=0):
    rows=[];opening=float(cash)
    for i in range(1,months+1):
        rev=revenue*((1+revenue_growth_rate)**(i-1));exp=expenses*((1+expense_growth_rate)**(i-1))+hiring_monthly_cost;collected=0 if i<=payment_delay_months else rev;one=one_time_expenses if i==1 else 0;net=collected-exp-one;closing=opening+net
        rows.append({'month':i,'opening_cash':round(opening,2),'revenue':round(collected,2),'expenses':round(exp+one,2),'net_cash_flow':round(net,2),'closing_cash':round(closing,2)});opening=closing
    return pd.DataFrame(rows)
def hiring_impact(cash,burn,count,salary,months=6):
    extra=count*salary;new=burn+extra;base=calculate_runway(cash,burn);nr=calculate_runway(cash,new)
    return {'count':count,'salary':float(salary),'additional_monthly_payroll':float(extra),'baseline_burn':float(burn),'new_burn':float(new),'baseline_runway':base,'new_runway':nr,'runway_delta':None if base is None or nr is None else round(nr-base,4),'six_month_cash_impact':float(extra*months)}
