import pandas as pd
def detect_anomalies(t,ap=None,runway=None,threshold_months=6):
    if t.empty:return []
    out=[];x=t.copy();x['amount']=pd.to_numeric(x.amount,errors='coerce');o=x[x.type.str.lower()=='outflow'].copy()
    if len(o):
        mean=float(o.amount.mean());std=float(o.amount.std(ddof=0) or 0);cut=max(mean*2.5,mean+2*std)
        for _,r in o[o.amount>cut].iterrows():out.append({'severity':'HIGH','type':'Unusually large transaction','what':f'{r.vendor} {r.category} ${r.amount:,.0f}','why':f'Amount exceeds anomaly threshold of ${cut:,.0f}.','supporting_data':{'date':str(r.date),'amount':float(r.amount)},'next_step':'Review invoice, business purpose, and approval evidence.','requires_review':True})
        o['month']=pd.to_datetime(o.date).dt.to_period('M').astype(str);last=o.month.max()
        for v in o.loc[o.month==last,'vendor'].astype(str).unique():
            if (o.loc[o.vendor.astype(str)==v,'month']<last).sum()==0:out.append({'severity':'MEDIUM','type':'New vendor','what':f'First observed outflow to {v}.','why':'Vendor has no prior transaction history in the supplied dataset.','supporting_data':{'vendor':v},'next_step':'Confirm vendor onboarding and supporting documentation.','requires_review':True})
    if ap is not None and len(ap):
        a=ap.copy();a['due_date']=pd.to_datetime(a.due_date,errors='coerce')
        for _,r in a[a.status.str.lower()=='open'].sort_values('due_date').head(3).iterrows():out.append({'severity':'MEDIUM','type':'Upcoming payable','what':f'{r.vendor} ${r.amount:,.0f} due {r.due_date.date()}','why':'Open payable creates a known future cash outflow.','supporting_data':{'vendor':r.vendor,'amount':float(r.amount)},'next_step':'Confirm payment timing and cash availability.','requires_review':True})
    if runway is not None and runway<threshold_months:out.append({'severity':'HIGH','type':'Low runway','what':f'Runway is approximately {runway:.1f} months.','why':f'Runway is below the configured {threshold_months:.1f}-month review threshold.','supporting_data':{'runway_months':runway},'next_step':'Review near-term hiring, spend, collections, and financing plans with finance leadership.','requires_review':True})
    return out
