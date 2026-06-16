from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import get_conn
from .routers import mandatory, analytics, dashboard, sources

app = FastAPI(
    title="German Accident Data API — Participant Count Schema",
    description="""
Analytical REST API for German road accident open data.

## Schema Design
This API uses a **participant count schema**: each accident row stores how many
of each participant type were involved (`cyclists`, `cars`, `pedestrians`,
`motorcycles`, `trucks`, `others` as INTEGER columns).

This differs from boolean flags (0/1 per type) and from separate participant rows.
It enables direct aggregation: `SUM(cyclists)` gives total cyclist-involvements.

## Data Sources
- Unfallatlas (accidents with personal injury, 2021–2023), dl-de/by-2-0
- Accident rate per 10,000 per city (aggregated statistics)

## License
All data: **dl-de/by-2-0** — Datenlizenz Deutschland – Namensnennung – Version 2.0
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM accidents")
            count = cur.fetchone()[0]
    print(f"DB ready | {count} accidents | API: http://localhost:8000 | Docs: http://localhost:8000/api/docs")


app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(mandatory.router, prefix="/api/mandatory", tags=["Mandatory Questions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(sources.router,   prefix="/api/sources",   tags=["Data Sources"])


@app.get("/health")
def health():
    return {"status": "ok", "schema": "participant-count", "docs": "/api/docs"}
