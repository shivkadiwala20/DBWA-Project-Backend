from fastapi import APIRouter
from ..db import query

router = APIRouter()


@router.get("/", summary="All imported data sources with provenance info")
def list_sources():
    rows = query("""
        SELECT id, name, origin_url, file_name, license,
               retrieved_at, records_loaded, records_skipped, status, error_notes
        FROM data_sources ORDER BY retrieved_at DESC
    """)
    return {"sources": rows}


@router.get("/health", summary="Quick DB health check")
def health():
    rows = query("SELECT COUNT(*) AS total FROM accidents")
    return {"total_accidents": rows[0]['total'], "status": "ok"}
