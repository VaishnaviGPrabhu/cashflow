import os,re,json
from .prompts import SYSTEM_PROMPT
class CashFlowAgent:
    def __init__(self,tools):
        self.tools=tools;self.model=os.getenv('ANTHROPIC_MODEL','').strip();self.client=None
        if os.getenv('ANTHROPIC_API_KEY') and self.model:
            try:
                from anthropic import Anthropic
                self.client=Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
            except Exception:self.client=None
    @property
    def ai_enabled(self):return self.client is not None
    def deterministic_answer(self,q):
        q=q.lower()
        if 'runway' in q:
            r=self.tools.calculate_runway()
            return "I don't have enough data to determine that. Monthly burn is not positive." if r['runway_months'] is None else f"Runway is approximately **{r['runway_months']:.1f} months** based on current cash of ${r['cash']:,.0f} and deterministic monthly burn of ${r['monthly_burn']:,.0f}.\n\n**Type:** ACTUAL + deterministic calculation.\n\n**Sources:** `calculate_runway()`."
        if 'hire' in q:
            m=re.search(r'(\d+)\s+(?:engineers?|employees?|people)',q);n=int(m.group(1)) if m else 2;r=self.tools.get_hiring_impact(n,12000)
            return f"Hiring {n} engineers at $12,000/month adds **${r['additional_monthly_payroll']:,.0f}/month**. Runway changes from **{r['baseline_runway']:.1f}** to **{r['new_runway']:.1f} months** ({r['runway_delta']:+.1f} months).\n\n**Type:** SCENARIO. **Source:** `get_hiring_impact()`."
        if 'risk' in q or 'anomal' in q:
            rs=self.tools.detect_anomalies()
            return "No configured anomaly rule fired." if not rs else "Items requiring human review:\n"+"\n".join(f"- **{r['severity']}** — {r['what']}" for r in rs[:6])
        if 'cash' in q:return f"Current cash is **${self.tools.get_current_cash()['current_cash']:,.0f}** from the synthetic dataset."
        return "I don't have enough data to determine that. Ask about cash, runway, risks, or hiring impact."
    def answer(self,q):
        if not self.ai_enabled:return "Demo mode — deterministic analysis available. Configure `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` to enable the Claude Analyst.\n\n"+self.deterministic_answer(q)
        context=json.dumps({'cash':self.tools.get_current_cash(),'burn':self.tools.calculate_monthly_burn(),'runway':self.tools.calculate_runway(),'risks':self.tools.detect_anomalies()},default=str)
        try:
            msg=self.client.messages.create(model=self.model,max_tokens=700,system=SYSTEM_PROMPT,messages=[{'role':'user','content':f'Question: {q}\nVerified context:\n{context}'}])
            return next((b.text for b in msg.content if getattr(b,'type',None)=='text'),'No textual response returned.')
        except Exception as exc:return f"Claude API unavailable; using deterministic demo mode.\n\n{self.deterministic_answer(q)}\n\nContained API error: {type(exc).__name__}."
