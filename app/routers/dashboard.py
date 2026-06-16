from fastapi import APIRouter
from ..db import query

router = APIRouter()


@router.get("/summary", summary="All KPIs in one call for the dashboard page")
def summary():
    rows = query("""
        SELECT
            COUNT(*)                                          AS total_accidents,
            SUM(CASE WHEN severity = 1 THEN 1 ELSE 0 END)    AS fatal,
            SUM(pedestrians)                                  AS total_pedestrian_involvements,
            SUM(cyclists)                                     AS total_cyclist_involvements,
            COUNT(DISTINCT state_ags)                         AS states_count,
            MIN(year)                                         AS earliest_year,
            MAX(year)                                         AS latest_year
        FROM accidents
    """)
    r = rows[0]

    years = query("SELECT DISTINCT year FROM accidents ORDER BY year")

    top = query("""
        SELECT state_ags AS ags, COUNT(*) AS count
        FROM accidents WHERE year = (SELECT MAX(year) FROM accidents)
        GROUP BY state_ags ORDER BY count DESC LIMIT 1
    """)

    return {
        "total_accidents":               r['total_accidents'],
        "fatal_accidents":               r['fatal'],
        "total_pedestrian_involvements": r['total_pedestrian_involvements'],
        "total_cyclist_involvements":    r['total_cyclist_involvements'],
        "states_with_data":              r['states_count'],
        "earliest_year":                 r['earliest_year'],
        "latest_year":                   r['latest_year'],
        "years_available":               [row['year'] for row in years],
        "top_state_latest_year":         top[0] if top else None,
    }
