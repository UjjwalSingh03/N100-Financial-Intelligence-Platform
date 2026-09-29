"""Day 14 validation helper tests."""
from pathlib import Path
from scripts.day14_sprint_review import check_edge_log

def test_edge_log_requires_category_and_reason(tmp_path: Path):
    path=tmp_path/"ratio_edge_cases.log"
    path.write_text("# header\nROCE | company_id=TCS | year=2025 | category=formula discrepancy | reason=source differs\n", encoding="utf-8")
    ok,count,errors=check_edge_log(path)
    assert ok is True and count == 1 and errors == []

def test_edge_log_rejects_undocumented_anomaly(tmp_path: Path):
    path=tmp_path/"ratio_edge_cases.log"
    path.write_text("ROE | company_id=TCS | year=2025 | category=formula discrepancy\n", encoding="utf-8")
    ok,count,errors=check_edge_log(path)
    assert ok is False and count == 1
    assert any("missing explanation" in item for item in errors)
