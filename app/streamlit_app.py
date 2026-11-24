import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st,pandas as pd
from core.data_loader import load_demo_data,read_csv_bytes
from core.validators import validate_all
from core.calculations import current_cash,net_cash_flow,monthly_burn,calculate_runway,scenario_cashflow
from core.forecasting import build_forecast,forecast_runway
from core.anomaly_detection import detect_anomalies
from agent.tools import FinanceTools
from agent.agent import CashFlowAgent
from app.components.charts import cash_chart,flow_chart
from app.components.tables import kpis
from evaluations.evaluation_runner import run_evaluations
st.set_page_config(page_title='AI CashFlow Copilot',page_icon='💧',layout='wide')
st.title('AI CashFlow Copilot');st.caption('AI-assisted cash-flow analysis, forecasting and scenario planning.')
st.warning('Prototype for financial analysis and workflow demonstration. Outputs are decision-support drafts and require review by a qualified finance professional.')
@st.cache_data
def demo():return load_demo_data()
if 'data' not in st.session_state:st.session_state.data=demo()
data=st.session_state.data
with st.sidebar:
 st.header('Navigation');page=st.radio('Go to',['Overview','Forecast','Scenarios','Risk Review','AI Analyst','Evaluation','Methodology'])
 st.divider();st.caption('Synthetic/demo dataset: NovaTech Labs')
 up=st.file_uploader('Upload transactions CSV',type=['csv'])
 if up:
  df,issues=read_csv_bytes('transactions',up.getvalue())
  if any(i.severity=='HIGH' for i in issues):st.error('Blocking validation issue; demo data remains active.')
  else:d=dict(data);d['transactions']=df;st.session_state.data=d;st.success('Transactions loaded.')
cash=current_cash(data['transactions']);burn=monthly_burn(data['recurring_expenses'],data['payroll'],data['transactions']);runway=calculate_runway(cash,burn);net=net_cash_flow(data['transactions'])
tools=FinanceTools(data);agent=CashFlowAgent(tools);forecast=build_forecast(cash,data['revenue_assumptions'],data['recurring_expenses'],data['payroll'],data['hiring_plan']);risks=detect_anomalies(data['transactions'],data['accounts_payable'],runway)
if page=='Overview':
 kpis(cash,burn,runway,net);a,b=st.columns(2);a.plotly_chart(cash_chart(forecast),use_container_width=True);b.plotly_chart(flow_chart(forecast),use_container_width=True);st.subheader('Risk review')
 for r in risks[:6]:st.write(f"**{r['severity']} — {r['type']}**: {r['what']} — Requires review.")
 with st.expander('Sources / traceability'):st.write(['transactions.csv + synthetic starting cash','recurring_expenses.csv + payroll.csv','calculate_runway()'])
elif page=='Forecast':
 st.header('6-month forecast');st.caption('FORECAST values are assumptions-based, not actuals.');st.plotly_chart(cash_chart(forecast),use_container_width=True);st.dataframe(forecast,use_container_width=True);st.metric('Forecast runway','N/A' if forecast_runway(forecast) is None else f'{forecast_runway(forecast):.1f} months')
elif page=='Scenarios':
 st.header('Interactive scenario');rg=st.slider('Revenue growth / month',-0.2,0.2,0.03,0.01);eg=st.slider('Expense growth / month',-0.05,0.15,0.02,0.01);one=st.number_input('One-time expense',0,100000,0,1000);delay=st.slider('Payment delay (months)',0,2,0);r=float(data['revenue_assumptions'].expected_revenue.head(3).mean());e=r+burn;sc=scenario_cashflow(cash,r,e,6,rg,eg,one,delay);st.dataframe(sc,use_container_width=True);st.caption('SCENARIO: explicit assumptions, not actuals.')
elif page=='Risk Review':
 st.header('Risk review');st.caption('Rules flag patterns requiring review; they do not assert that a transaction is wrong or fraudulent.')
 for r in risks:
  with st.expander(f"{r['severity']} — {r['type']}"):st.write(r['what']);st.write('**Why:**',r['why']);st.write('**Supporting data:**',r['supporting_data']);st.write('**Next step:**',r['next_step'])
elif page=='AI Analyst':
 st.header('AI Analyst')
 if not agent.ai_enabled:st.info('Demo mode — deterministic analysis available. Configure ANTHROPIC_API_KEY and ANTHROPIC_MODEL to enable Claude.')
 q=st.chat_input('Ask about runway, cash, risks, or hiring impact…')
 if q:st.chat_message('user').write(q);st.chat_message('assistant').markdown(agent.answer(q))
elif page=='Evaluation':
 st.header('Evaluation dashboard');r=run_evaluations();s=r['summary'];st.write(f"**Total:** {s['total']} · **Passed:** {s['passed']} · **Failed:** {s['failed']} · **Pass rate:** {s['pass_rate']*100:.1f}%");st.dataframe(pd.DataFrame(r['results']),use_container_width=True)
 st.subheader('Trap cases');st.dataframe(pd.DataFrame(json.loads((Path(__file__).resolve().parents[1]/'evaluations/trap_cases.json').read_text())),use_container_width=True)
else:
 st.header('Methodology');st.markdown('**Data → Validation → Deterministic calculations → Tools → AI interpretation → Evaluation → Human review**\n\nFinancial arithmetic is deterministic and testable. AI interprets verified outputs. Human review remains required.');issues=validate_all(data)
 for i in issues:st.write(f'**{i.severity}** — {i.dataset}: {i.message}')
 if not issues:st.success('Demo datasets passed validation.')
