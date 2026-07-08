# Ethara Seat Allocation & Project Mapping System

Full-stack app for managing seat allocation across ~5,000 employees: employee
management, project mapping, seat allocation/release, new-joiner allocation,
search, a stats dashboard, and a natural-language AI assistant.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite for local/demo (swap `DATABASE_URL` env var for Postgres in prod)
- **AI Assistant:** Rule-based intent parser (offline, no API key needed). Designed
  so a real LLM call can be dropped in on top of the same intent handlers.

## Project Structure

```
backend/
  app/
    main.py          # FastAPI app + router registration
    database.py       # DB engine/session
    models.py          # SQLAlchemy models: Employee, Project, Seat, SeatAllocation
    schemas.py         # Pydantic request/response schemas
    seed.py            # Seed data generator (5000 employees, 5500 seats, etc.)
    routers/
      employees.py     # CRUD + search
      projects.py       # CRUD + list employees by project
      seats.py           # CRUD, /available, /allocate (with proximity logic), /release
      dashboard.py       # /summary, /project-utilization, /floor-utilization
      ai.py                # POST /ai/query natural-language assistant
  requirements.txt
```

## Running locally

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m app.seed        # generates seed data into ethara_seats.db
uvicorn app.main:app --reload
```
Visit `http://localhost:8000/docs` for interactive Swagger API docs.

**Frontend:**
```bash
cd frontend
npm install
npm run dev               # http://localhost:5173, expects backend at http://localhost:8000
```
Set `VITE_API_URL` in `frontend/.env` if the backend runs elsewhere.

## Frontend

React + Vite + Tailwind v4. Four screens:
- **Dashboard** — KPI cards, floor occupancy bars, project utilization table
- **Employees** — search by name/email/code, view detail, allocate/release seat
- **Floor Map** — the actual seating grid: pick a floor + zone, see every seat
  color-coded by status (available/occupied/reserved/maintenance), hover for
  seat number and bay
- **Assistant** — chat UI against `POST /ai/query`, with example prompts and
  an optional email field for "my seat" / "who's near me" questions

## Seed Data

`python -m app.seed` generates, matching the assessment spec:
- 5,000 employees across 10 projects (Indigo, Indreed, Mydreed, Preed, Serfy,
  Oreed, Bedegreed, Opreed, Serry, Kaary, Mered)
- 5 floors x 10 zones x 110 seats = 5,500 seats
- 500 available seats, 120 reserved, 30 in maintenance
- ~150 employees pending seat allocation

## Seat Allocation Logic (proximity)

`POST /seats/allocate` with just `employee_id`:
1. Uses `preferred_zone` if passed.
2. Otherwise finds the zone where the most active teammates on the same
   project already sit, and allocates there.
3. Falls back to any available seat in any zone if the preferred/team zone
   has none free.

## AI Assistant

`POST /ai/query` with `{"query": "...", "email": "optional@ethara.ai"}` handles:
- "Where is employee X seated?" / "Where is my seat?" (with email)
- "Which project is X assigned to?"
- "Show available seats on Floor N"
- "How many seats are occupied for Project X?"
- "Who is sitting near me?" (with email)
- Guidance on allocating a seat for a new joiner

This is a deterministic keyword/regex intent parser — it works fully offline
and is easy to demo without any external API dependency. A real LLM (Claude/
OpenAI) can be layered on top to handle free-form phrasing the rules miss,
using the same underlying data-fetch functions.

## What's not yet built (next steps)

- Deployment (Railway/Render/Vercel) + live URLs
- CSV bulk upload for employee/seat data
- Auth / role-based access (Employee vs HR/Admin)

## Business Rules Enforced

- One employee → one active seat allocation (checked in `/seats/allocate`)
- One seat → one active employee (seat marked `occupied` on allocation)
- Released seats return to `available`
- Duplicate employee email rejected
- Duplicate seat number on same floor/zone rejected
