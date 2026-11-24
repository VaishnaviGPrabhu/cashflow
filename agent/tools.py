from core.calculations import current_cash,monthly_burn,calculate_runway,variance,hiring_impact,scenario_cashflow
from core.anomaly_detection import detect_anomalies
class FinanceTools:
    def __init__(self,data,starting_cash=250000):self.data=data;self.starting_cash=starting_cash
    def get_current_cash(self):return {'current_cash':current_cash(self.data['transactions'],self.starting_cash),'source':'transactions + synthetic starting cash'}
    def get_transactions(self,limit=100):return self.data['transactions'].head(limit).to_dict('records')
    def get_accounts_receivable(self):return self.data['accounts_receivable'].to_dict('records')
    def get_accounts_payable(self):return self.data['accounts_payable'].to_dict('records')
    def get_recurring_expenses(self):return self.data['recurring_expenses'].to_dict('records')
    def get_payroll(self):return self.data['payroll'].to_dict('records')
    def get_revenue_assumptions(self):return self.data['revenue_assumptions'].to_dict('records')
    def calculate_monthly_burn(self):return {'monthly_burn':monthly_burn(self.data['recurring_expenses'],self.data['payroll'],self.data['transactions']),'source':'deterministic calculation'}
    def calculate_runway(self):
        c=self.get_current_cash()['current_cash'];b=self.calculate_monthly_burn()['monthly_burn'];return {'cash':c,'monthly_burn':b,'runway_months':calculate_runway(c,b),'source':'calculate_runway()'}
    def calculate_variance(self,current,previous):return variance(current,previous)
    def run_cashflow_scenario(self,revenue_growth=0,expense_growth=0,one_time_expenses=0,payment_delay_months=0,months=6):
        c=self.get_current_cash()['current_cash'];r=float(self.data['revenue_assumptions'].expected_revenue.head(3).mean());e=r+self.calculate_monthly_burn()['monthly_burn']
        return {'forecast':scenario_cashflow(c,r,e,months,revenue_growth,expense_growth,one_time_expenses,payment_delay_months).to_dict('records'),'source':'run_cashflow_scenario()'}
    def detect_anomalies(self):return detect_anomalies(self.data['transactions'],self.data['accounts_payable'],self.calculate_runway()['runway_months'])
    def get_hiring_impact(self,count,salary):return hiring_impact(self.get_current_cash()['current_cash'],self.calculate_monthly_burn()['monthly_burn'],count,salary)
TOOL_SCHEMAS=[
 {'name':'get_current_cash','description':'Return current synthetic cash.','input_schema':{'type':'object','properties':{}}},
 {'name':'get_transactions','description':'Retrieve transactions.','input_schema':{'type':'object','properties':{'limit':{'type':'integer'}}}},
 {'name':'get_accounts_receivable','description':'Retrieve AR.','input_schema':{'type':'object','properties':{}}},
 {'name':'get_accounts_payable','description':'Retrieve AP.','input_schema':{'type':'object','properties':{}}},
 {'name':'calculate_monthly_burn','description':'Deterministic monthly burn.','input_schema':{'type':'object','properties':{}}},
 {'name':'calculate_runway','description':'Deterministic runway.','input_schema':{'type':'object','properties':{}}},
 {'name':'calculate_variance','description':'Deterministic variance.','input_schema':{'type':'object','properties':{'current':{'type':'number'},'previous':{'type':'number'}}}},
 {'name':'run_cashflow_scenario','description':'Deterministic scenario.','input_schema':{'type':'object','properties':{'revenue_growth':{'type':'number'},'expense_growth':{'type':'number'},'one_time_expenses':{'type':'number'},'payment_delay_months':{'type':'integer'},'months':{'type':'integer'}}}},
 {'name':'detect_anomalies','description':'Detect review-required patterns.','input_schema':{'type':'object','properties':{}}},
 {'name':'get_hiring_impact','description':'Deterministic hiring impact.','input_schema':{'type':'object','properties':{'count':{'type':'integer'},'salary':{'type':'number'}}}}
]