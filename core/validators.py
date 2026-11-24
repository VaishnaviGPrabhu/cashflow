import pandas as pd
from .models import ValidationIssue
SCHEMAS={
'transactions':{'required':['date','type','category','vendor','amount'],'numeric':['amount'],'date':['date'],'nonnegative':['amount']},
'accounts_receivable':{'required':['customer','invoice_date','due_date','amount','status'],'numeric':['amount'],'date':['invoice_date','due_date'],'nonnegative':['amount']},
'accounts_payable':{'required':['vendor','invoice_date','due_date','amount','status'],'numeric':['amount'],'date':['invoice_date','due_date'],'nonnegative':['amount']},
'recurring_expenses':{'required':['vendor','category','monthly_amount'],'numeric':['monthly_amount'],'nonnegative':['monthly_amount']},
'payroll':{'required':['employee_id','role','start_date','monthly_salary'],'numeric':['monthly_salary'],'date':['start_date'],'nonnegative':['monthly_salary']},
'revenue_assumptions':{'required':['month','expected_revenue'],'numeric':['expected_revenue'],'date':['month'],'nonnegative':['expected_revenue']},
'hiring_plan':{'required':['month','role','count','monthly_salary'],'numeric':['count','monthly_salary'],'date':['month'],'nonnegative':['count','monthly_salary']}}
def validate_dataframe(name,df):
    if df is None or df.empty:return [ValidationIssue('HIGH',name,'Dataset is empty.')]
    s=SCHEMAS.get(name)
    if not s:return [ValidationIssue('MEDIUM',name,'Unknown dataset schema; review manually.')]
    out=[];missing=[c for c in s['required'] if c not in df.columns]
    out += [ValidationIssue('HIGH',name,f'Missing required column: {c}',field=c) for c in missing]
    if missing:return out
    if int(df.duplicated().sum()):out.append(ValidationIssue('MEDIUM',name,f'{int(df.duplicated().sum())} duplicate record(s) detected.'))
    for c in s.get('numeric',[]):
        bad=pd.to_numeric(df[c],errors='coerce').isna() & df[c].notna()
        if int(bad.sum()):out.append(ValidationIssue('HIGH',name,f'Invalid numeric value(s) in {c}: {int(bad.sum())}.',field=c))
    for c in s.get('date',[]):
        bad=pd.to_datetime(df[c],errors='coerce').isna() & df[c].notna()
        if int(bad.sum()):out.append(ValidationIssue('HIGH',name,f'Invalid date value(s) in {c}: {int(bad.sum())}.',field=c))
    for c in s.get('nonnegative',[]):
        bad=pd.to_numeric(df[c],errors='coerce')<0
        if int(bad.sum()):out.append(ValidationIssue('MEDIUM',name,f'Negative value(s) detected in {c}; no silent correction was applied.',field=c))
    return out
def validate_all(data):return [i for n,d in data.items() for i in validate_dataframe(n,d)]
