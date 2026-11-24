from core.data_loader import load_demo_data
from agent.tools import FinanceTools,TOOL_SCHEMAS
def test_tools():
 t=FinanceTools(load_demo_data());assert len(TOOL_SCHEMAS)>=7 and t.calculate_runway()['runway_months'] is not None
