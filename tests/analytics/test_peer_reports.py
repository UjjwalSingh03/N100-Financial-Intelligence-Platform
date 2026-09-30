import pandas as pd
from src.analytics.peer import METRICS, _percent_rank
from scripts.peer_reports import _metric_percentile, add_fcf_score

def test_percentile_boundaries():
    values = pd.Series([10.0, 20.0, 30.0])
    assert _metric_percentile(values).tolist() == [0.0, 0.5, 1.0]

def test_de_percentile_is_inverted():
    values = pd.Series([0.0, 1.0, 2.0])
    assert _metric_percentile(values, higher=False).tolist() == [1.0, 0.5, 0.0]

def test_fcf_score_is_0_to_100():
    frame = pd.DataFrame({"company_id": ["A", "B", "C"], "free_cash_flow_cr": [10, 20, 30]})
    groups = pd.DataFrame({"company_id": ["A", "B", "C"], "peer_group_name": ["G", "G", "G"]})
    out = add_fcf_score(frame, groups)
    assert out["fcf_score"].tolist() == [0.0, 50.0, 100.0]

def test_required_radar_metrics():
    assert len(METRICS) == 10
