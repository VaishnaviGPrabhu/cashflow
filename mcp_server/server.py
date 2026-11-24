from core.data_loader import load_demo_data
from agent.tools import FinanceTools
def create_server():
    try:from mcp.server.fastmcp import FastMCP
    except ImportError as e:raise RuntimeError('Install a compatible MCP Python package to run the optional server.') from e
    f=FinanceTools(load_demo_data());m=FastMCP('AI CashFlow Copilot')
    for n in ['get_current_cash','get_transactions','get_accounts_receivable','get_accounts_payable','calculate_runway','calculate_variance','run_cashflow_scenario']:m.tool()(getattr(f,n))
    return m
if __name__=='__main__':create_server().run()
