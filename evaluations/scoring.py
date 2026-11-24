def within(v,e,t):return (v is None and e is None) if e is None else (v is not None and abs(float(v)-float(e))<=t)
def score_results(r):
 p=sum(bool(x['passed']) for x in r);return {'total':len(r),'passed':p,'failed':len(r)-p,'pass_rate':p/len(r) if r else 0}
