"""Day 44 documentation and quality audit; run from repository root.

Creates a public-function docstring inventory and copies only existing, explicitly
listed deliverables into output/final_deliverables (no fabricated placeholders).
"""
import ast
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"output"/"final_deliverables"
DELIVERABLES=[
"db/schema.sql","src/etl/loader.py","src/etl/normaliser.py",
"src/etl/validator.py","src/etl/database_loader.py",
"output/load_audit.csv","output/validation_failures.csv",
"notebooks/exploratory_queries.sql","output/ratio_edge_cases.log",
"output/capital_allocation.csv","output/screener_output.xlsx",
"output/peer_comparison.xlsx","output/analysis_parsed.csv",
"output/pros_cons_generated.csv","output/cashflow_intelligence.xlsx",
"output/distress_alerts.csv","output/capital_allocation_audit.csv",
"output/cluster_labels.csv","output/cluster_profiles.csv",
"output/correlation_matrix.csv","output/portfolio_stats.csv",
"docs/analyst_guide.pdf","reports/pytest_report.html",
]

def audit_docstrings():
    """List public top-level functions and public class methods missing docstrings."""
    missing=[]
    for file in (ROOT/"src").rglob("*.py"):
        try: tree=ast.parse(file.read_text(encoding="utf-8"),filename=str(file))
        except (SyntaxError,UnicodeError) as exc:
            missing.append({"file":str(file.relative_to(ROOT)),"error":str(exc)})
            continue
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                if not ast.get_docstring(node): missing.append({"file":str(file.relative_to(ROOT)),"line":node.lineno,"function":node.name})
            if isinstance(node,ast.ClassDef) and not node.name.startswith("_"):
                for method in node.body:
                    if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)) and not method.name.startswith("_") and not ast.get_docstring(method):
                        missing.append({"file":str(file.relative_to(ROOT)),"line":method.lineno,"function":node.name+"."+method.name})
    return missing

def archive():
    """Copy existing deliverables and record missing items without manufacturing files."""
    DEST.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for rel in DELIVERABLES:
        src=ROOT/rel
        if src.is_file():
            target=DEST/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,target)
            status="archived"
        else: status="missing"
        manifest.append({"path":rel,"status":status})
    (DEST/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

def main():
    """Generate docstring audit and archive manifest; fail when deliverables are absent."""
    DEST.mkdir(parents=True,exist_ok=True)
    missing=audit_docstrings()
    (DEST/"docstring_audit.json").write_text(json.dumps(missing,indent=2),encoding="utf-8")
    manifest=archive()
    absent=[m["path"] for m in manifest if m["status"]=="missing"]
    print(f"Public functions missing docstrings: {len(missing)}; archived: {23-len(absent)}/23")
    if missing: print("See output/final_deliverables/docstring_audit.json")
    if absent: print("Missing deliverables:\\n" + "\\n".join(absent))
    return int(bool(missing or absent))

if __name__=="__main__":
    raise SystemExit(main())
