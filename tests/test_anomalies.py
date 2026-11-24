from core.data_loader import load_demo_data
from core.calculations import *
from core.anomaly_detection import detect_anomalies
def test_anomalies():
 d=load_demo_data();r=detect_anomalies(d['transactions'],d['accounts_payable'],calculate_runway(current_cash(d['transactions']),monthly_burn(d['recurring_expenses'],d['payroll'],d['transactions'])));assert len(r)>0 and all(x['requires_review'] for x in r)
