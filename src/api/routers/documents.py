"""Annual report links and conservative URL validation."""
import sqlite3
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException
from src.api.db import get_connection
from .companies import company, columns, records

router = APIRouter(tags=["documents"])

@router.get("/companies/{ticker}/documents")
def documents(ticker: str, db: sqlite3.Connection = Depends(get_connection)):
    cid = company(db, ticker)["id"]
    if not {"company_id", "document_url"} <= columns(db, "documents"):
        raise HTTPException(503, "Documents table unavailable")
    rows = records(db, "SELECT * FROM documents WHERE company_id=? ORDER BY document_date DESC", (cid,))
    # Syntax validation only: does not assert remote availability without a live HTTP check.
    for row in rows:
        u = urlsplit(row.get("document_url") or "")
        row["is_url_valid"] = u.scheme in ("https", "http") and bool(u.netloc) and not bool(u.username or u.password)
        row["url_validation_method"] = "syntax_only"
    return rows
