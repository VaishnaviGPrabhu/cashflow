import plotly.express as px
def cash_chart(df):return px.line(df,x='month',y='closing_cash',markers=True,title='Forecast closing cash')
def flow_chart(df):return px.bar(df,x='month',y=['revenue','expenses'],barmode='group',title='Inflows vs outflows')
