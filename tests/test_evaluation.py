from evaluations.evaluation_runner import run_evaluations
def test_eval():
 r=run_evaluations();assert r['summary']['total']==10 and r['summary']['failed']==0
