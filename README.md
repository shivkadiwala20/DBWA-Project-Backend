# German Accident Data Platform — Participant Count Schema
Python 3.11 + FastAPI + psycopg2 + PostgreSQL + React + MUI

## Schema Design
Each accident row stores participant involvement as INTEGER COUNTS:
  cyclists INT, cars INT, pedestrians INT, motorcycles INT, trucks INT, others INT

Enables direct aggregation:
  SELECT SUM(pedestrians) FROM accidents WHERE year = 2023

## Prerequisites
- Python 3.11+, Node.js 18+, PostgreSQL 15+

## PostgreSQL Setup
```bash
psql postgres -c "CREATE DATABASE dbw_v3;"
psql postgres -c "CREATE USER dbw_user WITH PASSWORD 'dbw2026';"
psql postgres -c "GRANT ALL ON DATABASE dbw_v3 TO dbw_user;"
psql "postgresql://dbw_user:dbw2026@localhost:5432/dbw_v3" -f app/sql/init.sql
```

## Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Copy CSV files into data/ folder (already done if you used setup)
DATABASE_URL="postgresql://dbw_user:dbw2026@localhost:5432/dbw_v3" python -m app.etl.pipeline
DATABASE_URL="postgresql://dbw_user:dbw2026@localhost:5432/dbw_v3" uvicorn app.main:app --reload --port 8000
```

## Frontend
```bash
cd frontend
npm install
npm run dev
```

## URLs
- API:   http://localhost:8000
- Docs:  http://localhost:8000/api/docs
- UI:    http://localhost:5173

## Test Mandatory Questions
```bash
curl http://localhost:8000/api/mandatory/earliest-year
curl "http://localhost:8000/api/mandatory/accidents-by-state-year?state=Sachsen&year=2023"
curl "http://localhost:8000/api/mandatory/earliest-year-by-state?state=Nordrhein-Westfalen"
curl "http://localhost:8000/api/mandatory/earliest-year-by-state?state=Mecklenburg-Vorpommern"
curl "http://localhost:8000/api/mandatory/pedestrian-accidents?state=Berlin&year=2023"
curl "http://localhost:8000/api/mandatory/rate-per-100k?year=2023"
curl "http://localhost:8000/api/mandatory/fatal-by-state?year=2023"
```
