from core.data_loader import load_demo_data
from core.calculations import current_cash
from core.forecasting import build_forecast
def test_forecast():
 d=load_demo_data();f=build_forecast(current_cash(d['transactions']),d['revenue_assumptions'],d['recurring_expenses'],d['payroll'],d['hiring_plan']);assert len(f)==6
