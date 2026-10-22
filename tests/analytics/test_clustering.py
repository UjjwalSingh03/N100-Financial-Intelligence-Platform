"""Day 36 clustering unit tests (production run requires db/nifty100.db)."""
import numpy as np
import pandas as pd
import pytest
from src.analytics.clustering import FEATURES, impute_features, label_clusters, generate


def test_sector_median_and_global_fallback():
    frame = pd.DataFrame({"sector": ["IT", "IT", "Bank", "Bank"]})
    for name in FEATURES:
        frame[name] = [10.0, np.nan, np.nan, 20.0]
    actual = impute_features(frame)
    assert actual.loc[1, FEATURES[0]] == 10
    assert actual.loc[2, FEATURES[0]] == 20
    assert not actual[list(FEATURES)].isna().any().any()


def test_fully_missing_metric_fails():
    frame = pd.DataFrame({"sector": ["IT", "Bank"]})
    for name in FEATURES:
        frame[name] = [1.0, 2.0]
    frame[FEATURES[0]] = np.nan
    with pytest.raises(ValueError, match="No observed values"):
        impute_features(frame)


def test_five_unique_archetypes():
    names = label_clusters(np.array([[i, 0, i, i, i] for i in range(5)], dtype=float))
    assert set(names) == set(range(5))
    assert len(set(names.values())) == 5


def test_production_clustering_if_database_available(tmp_path):
    from pathlib import Path
    db = Path("db/nifty100.db")
    if not db.exists():
        pytest.skip("Production DB unavailable")
    result = generate(db, tmp_path/"cluster_labels.csv", tmp_path/"elbow_plot.png")
    assert len(result) == result.company_id.nunique() == 92
    assert set(result.cluster_id) == set(range(5))
    assert (result.distance_from_centroid >= 0).all()
    assert (tmp_path/"elbow_plot.png").stat().st_size > 0
