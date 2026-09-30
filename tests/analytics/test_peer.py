import pandas as pd
from src.analytics.peer import METRICS,_percent_rank,compute_peer_percentiles

def test_percent_rank(): assert _percent_rank(pd.Series([10.,20.,30.])).tolist()==[0.,.5,1.]
def test_ties_use_rank_min(): assert _percent_rank(pd.Series([10.,20.,20.,30.])).tolist()==[0.,1/3,1/3,1.]
def test_de_is_inverted():
    m=pd.DataFrame({"company_id":["A","B","C"],"year":[2025]*3,**{x:[1.,2.,3.] for x in METRICS}}); m["debt_to_equity"]=[0.,1.,2.]
    g=pd.DataFrame({"company_id":["A","B","C"],"peer_group_name":["G"]*3}); o,_=compute_peer_percentiles(m,g)
    assert o[o.metric=="debt_to_equity"].sort_values("company_id").percentile_rank.tolist()==[1.,.5,0.]
def test_all_ten_metrics():
    m=pd.DataFrame({"company_id":["A","B"],"year":[2025,2025],**{x:[1.,2.] for x in METRICS}})
    g=pd.DataFrame({"company_id":["A","B"],"peer_group_name":["G","G"]}); o,_=compute_peer_percentiles(m,g)
    assert set(o.metric)==set(METRICS) and len(o)==20
def test_missing_group_message():
    m=pd.DataFrame({"company_id":["A"],"year":[2025],**{x:[1.] for x in METRICS}})
    o,msg=compute_peer_percentiles(m,pd.DataFrame(columns=["company_id","peer_group_name"]))
    assert o.empty and msg==["A: No peer group assigned"]
