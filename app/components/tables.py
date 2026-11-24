import streamlit as st
def kpis(cash,burn,runway,net):
 c=st.columns(4)
 vals=[f'${cash:,.0f}',f'${burn:,.0f}','N/A' if runway is None else f'{runway:.1f} mo',f'${net:,.0f}']
 for x,l,v in zip(c,['Current Cash','Monthly Burn','Runway','Net Cash Flow'],vals):x.metric(l,v)
