from fastapi import APIRouter, Query
from ..db import query

router = APIRouter()


@router.get("/by-state", summary="Accident count per state, optionally filtered by year")
def by_state(year: int = Query(None)):
    if year:
        rows = query("""
            SELECT state_ags AS ags, COUNT(*) AS count
            FROM accidents WHERE year = %s
            GROUP BY state_ags ORDER BY count DESC
        """, (year,))
    else:
        rows = query("""
            SELECT state_ags AS ags, COUNT(*) AS count
            FROM accidents GROUP BY state_ags ORDER BY count DESC
        """)
    from .mandatory import STATE_NAMES
    for r in rows:
        r['state_name'] = STATE_NAMES.get(r['ags'], r['ags'])
    return {"data": rows}


@router.get("/by-severity", summary="Accident count broken down by severity level")
def by_severity(state: str = Query(None), year: int = Query(None)):
    conditions, params = [], []
    if state:
        conditions.append("state_ags = %s")
        params.append(state)
    if year:
        conditions.append("year = %s")
        params.append(year)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = query(f"""
        SELECT
            severity,
            CASE severity WHEN 1 THEN 'Fatal'
                          WHEN 2 THEN 'Severe Injury'
                          WHEN 3 THEN 'Light Injury' END AS label,
            COUNT(*) AS count
        FROM accidents {where}
        GROUP BY severity ORDER BY severity
    """, params)
    return {"data": rows}


@router.get("/trend", summary="Year-over-year accident count (optionally for one state)")
def trend(state: str = Query(None)):
    if state:
        rows = query("""
            SELECT year, COUNT(*) AS count
            FROM accidents WHERE state_ags = %s
            GROUP BY year ORDER BY year
        """, (state,))
    else:
        rows = query("""
            SELECT year, COUNT(*) AS count
            FROM accidents GROUP BY year ORDER BY year
        """)
    return {"data": rows}


@router.get("/participant-totals", summary="Sum of each participant type across all accidents")
def participant_totals(year: int = Query(None), state: str = Query(None)):
    conditions, params = [], []
    if year:
        conditions.append("year = %s")
        params.append(year)
    if state:
        conditions.append("state_ags = %s")
        params.append(state)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = query(f"""
        SELECT
            SUM(cyclists)    AS total_cyclists,
            SUM(cars)        AS total_cars,
            SUM(pedestrians) AS total_pedestrians,
            SUM(motorcycles) AS total_motorcycles,
            SUM(trucks)      AS total_trucks,
            SUM(others)      AS total_others
        FROM accidents {where}
    """, params)
    r = rows[0]
    return {"data": [
        {"type": "cyclists",    "count": r['total_cyclists']    or 0},
        {"type": "cars",        "count": r['total_cars']        or 0},
        {"type": "pedestrians", "count": r['total_pedestrians'] or 0},
        {"type": "motorcycles", "count": r['total_motorcycles'] or 0},
        {"type": "trucks",      "count": r['total_trucks']      or 0},
        {"type": "others",      "count": r['total_others']      or 0},
    ]}


@router.get("/heatmap", summary="Hour × Weekday accident count matrix")
def heatmap(state: str = Query(None), year: int = Query(None)):
    conditions = ["hour IS NOT NULL", "weekday IS NOT NULL"]
    params = []
    if state:
        conditions.append("state_ags = %s")
        params.append(state)
    if year:
        conditions.append("year = %s")
        params.append(year)
    where = "WHERE " + " AND ".join(conditions)
    rows = query(f"""
        SELECT hour, weekday, COUNT(*) AS count
        FROM accidents {where}
        GROUP BY hour, weekday ORDER BY hour, weekday
    """, params)
    return {"data": rows}


@router.get("/top-states", summary="Top N states by accident count")
def top_states(year: int = Query(2023), limit: int = Query(5), metric: str = Query("count")):
    rows = query("""
        SELECT state_ags AS ags, COUNT(*) AS count
        FROM accidents WHERE year = %s
        GROUP BY state_ags ORDER BY count DESC LIMIT %s
    """, (year, limit))
    from .mandatory import STATE_NAMES
    for r in rows:
        r['state_name'] = STATE_NAMES.get(r['ags'], r['ags'])
    return {"data": rows}
