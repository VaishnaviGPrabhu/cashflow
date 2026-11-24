from pathlib import Path
import io,pandas as pd
from .validators import validate_dataframe
DATA_DIR=Path(__file__).resolve().parents[1]/'data'/'demo'
FILES={'transactions':'transactions.csv','accounts_receivable':'accounts_receivable.csv','accounts_payable':'accounts_payable.csv','recurring_expenses':'recurring_expenses.csv','payroll':'payroll.csv','revenue_assumptions':'revenue_assumptions.csv','hiring_plan':'hiring_plan.csv'}
def load_demo_data():return {k:pd.read_csv(DATA_DIR/v) for k,v in FILES.items()}
def read_csv_bytes(name,payload):
    df=pd.read_csv(io.BytesIO(payload));return df,validate_dataframe(name,df)
