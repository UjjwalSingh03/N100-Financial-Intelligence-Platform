from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def render():
    st.title("Reports")
    reports_dir = PROJECT_ROOT / "reports"
    if not reports_dir.exists():
        st.info("No reports directory is available yet.")
        return
    files = [p for p in reports_dir.rglob("*") if p.is_file()]
    if not files:
        st.info("No generated reports are available.")
        return
    for path in sorted(files):
        st.write(path.relative_to(PROJECT_ROOT).as_posix())
