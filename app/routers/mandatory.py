from fastapi import APIRouter, Query, HTTPException
from ..db import query

router = APIRouter()

STATE_NAMES = {
    '01': 'Schleswig-Holstein',  '02': 'Hamburg',
    '03': 'Niedersachsen',       '04': 'Bremen',
    '05': 'Nordrhein-Westfalen', '06': 'Hessen',
    '07': 'Rheinland-Pfalz',     '08': 'Baden-Württemberg',
    '09': 'Bayern',              '10': 'Saarland',
    '11': 'Berlin',              '12': 'Brandenburg',
    '13': 'Mecklenburg-Vorpommern', '14': 'Sachsen',
    '15': 'Sachsen-Anhalt',      '16': 'Thüringen',
}
BY_NAME = {v.lower(): k for k, v in STATE_NAMES.items()}
BY_NAME.update({
    'saxony': '14', 'bavaria': '09', 'nrw': '05', 'berlin': '11', 'hamburg': '02',
    'thuringia': '16', 'hesse': '06', 'saarland': '10', 'bremen': '04',
    'north rhine-westphalia': '05', 'mecklenburg-western pomerania': '13',
    'mecklenburg': '13', 'lower saxony': '03', 'saxony-anhalt': '15',
})


def resolve_state(name: str):
    s = name.strip()
    if s.isdigit() and len(s) <= 2:
        ags = s.zfill(2)
        return ags, STATE_NAMES.get(ags, ags)
    ags = BY_NAME.get(s.lower())
    if not ags:
        raise HTTPException(400, f"Unknown state: '{name}'")
    return ags, STATE_NAMES[ags]


@router.get("/earliest-year", summary="Q1: Earliest year in the complete dataset")
def earliest_year():
    rows = query("SELECT MIN(year) AS earliest_year FROM accidents")
    y = rows[0]['earliest_year']
    if y is None:
        raise HTTPException(404, "No data. Run ETL first.")
    return {"earliest_year": y, "license": "dl-de/by-2-0"}


@router.get("/accidents-by-state-year",
    summary="Q2: Total accidents with personal injury in a state for a given year")
def accidents_by_state_year(
    state: str = Query(..., description="State name or 2-digit AGS, e.g. 'Sachsen' or '14'"),
    year:  int  = Query(..., ge=2016, le=2025),
):
    state_ags, state_name = resolve_state(state)
    rows = query(
        "SELECT COUNT(*) AS count FROM accidents WHERE state_ags = %s AND year = %s",
        (state_ags, year)
    )
    return {"state": state_name, "year": year, "accident_count": rows[0]['count'],
            "license": "dl-de/by-2-0"}


@router.get("/earliest-year-by-state",
    summary="Q3/Q4: Earliest year with data for a given state")
def earliest_year_by_state(
    state: str = Query(..., description="e.g. 'Nordrhein-Westfalen', 'Mecklenburg-Vorpommern'")
):
    state_ags, state_name = resolve_state(state)
    rows = query(
        "SELECT MIN(year) AS earliest_year FROM accidents WHERE state_ags = %s",
        (state_ags,)
    )
    y = rows[0]['earliest_year']
    if y is None:
        raise HTTPException(404, f"No data for state: {state}")
    return {"state": state_name, "earliest_year": y}


@router.get("/pedestrian-accidents",
    summary="Q5: Accidents involving pedestrians in a state for a given year")
def pedestrian_accidents(
    state: str = Query(...),
    year:  int  = Query(..., ge=2016, le=2025),
):
    state_ags, state_name = resolve_state(state)
    rows = query(
        """
        SELECT COUNT(*) AS count
        FROM   accidents
        WHERE  state_ags = %s
          AND  year      = %s
          AND  pedestrians > 0
        """,
        (state_ags, year)
    )
    return {"state": state_name, "year": year, "pedestrian_accident_count": rows[0]['count']}


@router.get("/rate-per-100k",
    summary="Q6: Accident rate per 100,000 inhabitants by state (cross-source join)")
def rate_per_100k(
    year:  int = Query(2023),
    limit: int = Query(16, ge=1, le=20),
    order: str = Query("desc", enum=["asc", "desc"]),
):
    direction = "DESC" if order == "desc" else "ASC"
    rows = query(f"""
        SELECT
            a.state_ags                                                  AS ags,
            ''::text                                                     AS name,
            COUNT(a.id)                                                  AS accident_count,
            s.value                                                      AS population,
            ROUND(COUNT(a.id)::numeric / NULLIF(s.value,0) * 100000, 2) AS rate_per_100k
        FROM accidents a
        LEFT JOIN statistics s
               ON s.ags = a.state_ags
              AND s.year = a.year
              AND s.indicator = 'population'
        WHERE a.year = %s
        GROUP BY a.state_ags, s.value
        ORDER BY rate_per_100k {direction} NULLS LAST
        LIMIT %s
    """, (year, limit))
    for r in rows:
        r['name'] = STATE_NAMES.get(r['ags'], r['ags'])
    return {"year": year, "ranking": [{"rank": i + 1, **r} for i, r in enumerate(rows)]}


@router.get("/fatal-by-state",
    summary="Q7: Fatal accidents (severity=1) by state for a given year")
def fatal_by_state(year: int = Query(2023)):
    rows = query("""
        SELECT state_ags AS ags, COUNT(*) AS fatal_count
        FROM   accidents
        WHERE  year = %s AND severity = 1
        GROUP BY state_ags
        ORDER BY fatal_count DESC
    """, (year,))
    for r in rows:
        r['state_name'] = STATE_NAMES.get(r['ags'], r['ags'])
    return {"year": year, "data": rows}
