"""
ETL loader for Unfallatlas CSV files.

PARTICIPANT COLUMN MAPPING:
  CSV column  → accidents table column
  IstRad      → cyclists
  IstPKW      → cars
  IstFuss     → pedestrians
  IstKrad     → motorcycles
  IstGkfz     → trucks
  IstSonstige → others

Each CSV column contains 0 or 1 (was this participant type involved?).
We store them as integers (counts), not booleans.
"""
import hashlib
import pandas as pd
from pathlib import Path
from ..db import get_conn
import psycopg2.extras

STATE_NAMES = {
    '01': 'Schleswig-Holstein',     '02': 'Hamburg',
    '03': 'Niedersachsen',          '04': 'Bremen',
    '05': 'Nordrhein-Westfalen',    '06': 'Hessen',
    '07': 'Rheinland-Pfalz',        '08': 'Baden-Württemberg',
    '09': 'Bayern',                 '10': 'Saarland',
    '11': 'Berlin',                 '12': 'Brandenburg',
    '13': 'Mecklenburg-Vorpommern', '14': 'Sachsen',
    '15': 'Sachsen-Anhalt',         '16': 'Thüringen',
}


def build_ags(row) -> str:
    try:
        land  = str(int(float(row.get('ULAND',   0)))).zfill(2)
        rbez  = str(int(float(row.get('UREGBEZ', 0)))).zfill(1)
        kreis = str(int(float(row.get('UKREIS',  0)))).zfill(2)
        gem   = str(int(float(row.get('UGEMEINDE', 0)))).zfill(3)
        return land + rbez + kreis + gem
    except (ValueError, TypeError):
        return '00000000'


def clean_csv(filepath: Path) -> pd.DataFrame:
    df = pd.read_csv(filepath, sep=';', encoding='utf-8-sig', dtype=str, low_memory=False)
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]

    for col in ['XGCSWGS84', 'YGCSWGS84']:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', '.', regex=False),
                errors='coerce'
            )

    int_cols = ['UJAHR', 'UMONAT', 'USTUNDE', 'UWOCHENTAG', 'UKATEGORIE',
                'UART', 'UTYP1', 'ULICHTVERH',
                'IstRad', 'IstPKW', 'IstFuss', 'IstKrad', 'IstGkfz', 'IstSonstige']
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    before = len(df)
    df = df[df['UJAHR'].between(2016, 2025)]
    if 'XGCSWGS84' in df.columns:
        df = df[df['XGCSWGS84'].between(5.8, 15.1)]
        df = df[df['YGCSWGS84'].between(47.2, 55.1)]
    print(f"  Plausibility: removed {before - len(df)} invalid rows")

    df['ags']       = df.apply(build_ags, axis=1)
    df['state_ags'] = df['ags'].str[:2]

    return df


def load_accidents(filepath: Path, source_name: str, source_url: str = None) -> dict:
    """Full ETL for one Unfallatlas CSV file. Returns {"loaded": int, "skipped": int}"""
    checksum = hashlib.md5(filepath.read_bytes()).hexdigest()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO data_sources (name, origin_url, file_name, checksum, status)
                VALUES (%s, %s, %s, %s, 'running')
                RETURNING id
            """, (source_name, source_url, filepath.name, checksum))
            source_id = cur.fetchone()[0]

    df = clean_csv(filepath)

    rows = []
    for _, r in df.iterrows():
        rows.append({
            'source_id':     r.get('UIDENTSTLAE'),
            'year':          int(r['UJAHR']),
            'month':         int(r['UMONAT'])     if pd.notna(r.get('UMONAT'))     else None,
            'hour':          int(r['USTUNDE'])     if pd.notna(r.get('USTUNDE'))    else None,
            'weekday':       int(r['UWOCHENTAG'])  if pd.notna(r.get('UWOCHENTAG')) else None,
            'severity':      int(r.get('UKATEGORIE', 3)),
            'accident_type': int(r['UART'])        if pd.notna(r.get('UART'))       else None,
            'road_type':     int(r['UTYP1'])       if pd.notna(r.get('UTYP1'))      else None,
            'light_cond':    int(r['ULICHTVERH'])  if pd.notna(r.get('ULICHTVERH')) else None,
            'lon':           float(r['XGCSWGS84']) if pd.notna(r.get('XGCSWGS84')) else None,
            'lat':           float(r['YGCSWGS84']) if pd.notna(r.get('YGCSWGS84')) else None,
            'ags':           r['ags'],
            'state_ags':     r['state_ags'],
            'cyclists':      int(r.get('IstRad',      0)),
            'cars':          int(r.get('IstPKW',      0)),
            'pedestrians':   int(r.get('IstFuss',     0)),
            'motorcycles':   int(r.get('IstKrad',     0)),
            'trucks':        int(r.get('IstGkfz',     0)),
            'others':        int(r.get('IstSonstige', 0)),
            'data_source_id': source_id,
        })

    INSERT_SQL = """
        INSERT INTO accidents (
            source_id, year, month, hour, weekday,
            severity, accident_type, road_type, light_cond,
            lon, lat, ags, state_ags,
            cyclists, cars, pedestrians, motorcycles, trucks, others,
            data_source_id
        ) VALUES (
            %(source_id)s, %(year)s, %(month)s, %(hour)s, %(weekday)s,
            %(severity)s, %(accident_type)s, %(road_type)s, %(light_cond)s,
            %(lon)s, %(lat)s, %(ags)s, %(state_ags)s,
            %(cyclists)s, %(cars)s, %(pedestrians)s, %(motorcycles)s, %(trucks)s, %(others)s,
            %(data_source_id)s
        )
        ON CONFLICT (source_id, year) DO NOTHING
    """

    loaded = skipped = 0
    BATCH = 1000
    with get_conn() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), BATCH):
                batch = rows[i:i + BATCH]
                psycopg2.extras.execute_batch(cur, INSERT_SQL, batch, page_size=500)
                loaded  += cur.rowcount
                skipped += len(batch) - cur.rowcount
                print(f"  {i + len(batch)}/{len(rows)}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE data_sources
                SET status='success', records_loaded=%s, records_skipped=%s
                WHERE id=%s
            """, (loaded, skipped, source_id))

    print(f"  Done: {loaded} loaded, {skipped} skipped")
    return {"loaded": loaded, "skipped": skipped}


def load_rate_per_10k(filepath: Path) -> int:
    """Load accident_per_10000_per_city.csv into statistics table."""
    df = pd.read_csv(filepath, sep=';', encoding='utf-8-sig', skiprows=2, header=0)
    df.columns = [c.strip() for c in df.columns]
    loaded = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for _, r in df.iterrows():
                ags = str(r.get('schluessel', '')).strip().zfill(5)
                val = str(r.get('wert', '')).replace(',', '.')
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    continue
                cur.execute("""
                    INSERT INTO statistics (ags, indicator, year, value, source_name)
                    VALUES (%s, 'accident_rate_per_10k', 2023, %s, 'Unfallatlas Fallback')
                    ON CONFLICT (ags, indicator, year) DO NOTHING
                """, (ags, val))
                loaded += cur.rowcount
    print(f"  Loaded {loaded} rate-per-10k rows")
    return loaded
