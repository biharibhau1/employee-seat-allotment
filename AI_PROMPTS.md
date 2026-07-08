# AI_PROMPTS.md

AI tool used: **Claude** (Anthropic), via the Claude.ai chat/agentic coding
environment with a sandboxed Linux container (bash, file read/write,
ability to run and curl-test the server directly).

## Prompt 1 – Architecture

> [Uploaded the assessment spec document — "Vibe Coding Assessment: Ethara
> Seat Allocation & Project Mapping System.md" — as the brief.] Build the
> backend for this.

Claude decided on: FastAPI + SQLAlchemy + SQLite (swappable to Postgres via
`DATABASE_URL`), one router file per resource (employees/projects/seats/
dashboard/ai), Pydantic schemas separated from ORM models.

## Prompt 2 – Database

Derived directly from the "Database Model Suggestion" section of the spec:
`employees`, `projects`, `seats`, `seat_allocations`. Added `UniqueConstraint`
on `(floor, zone, seat_number)` to enforce "no duplicate seat number on same
floor/zone", and unique constraints on employee `email` and `employee_code`
to enforce "no duplicate employee email."

## Prompt 3 – Backend APIs

Implemented every endpoint listed in section 5 of the spec (Employee,
Project, Seat, Dashboard, AI Assistant APIs) with the exact paths/methods
given.

## Prompt 4 – Seat Allocation Logic

> "New joiners should be prioritized for available seats near their project
> team. If no seats are available in the preferred zone, system should
> suggest alternate zones."

Implemented `_find_best_zone_for_project()`: queries which zone currently
holds the most active seat-allocations for teammates on the same project,
and allocates there first; falls back to `preferred_zone` param if given, and
to any available seat as a last resort. Enforces "one employee = one active
seat" by rejecting allocation if an active allocation already exists.

## Prompt 5 – AI Assistant

No LLM API key is available in this sandbox, so Claude built a **rule-based
keyword/regex intent parser** as the required fallback ("If AI API is not
available, candidate can build a fallback keyword-based assistant"),
covering all six example queries from the spec (seat lookup, project
assignment, available seats by floor, occupancy by project, "who's near me",
new-joiner allocation guidance). The code is structured so a real Claude/
OpenAI call can be dropped in on top of the same DB-lookup functions later
without rewriting the data layer.

## Prompt 6 – Frontend

Built as React + Vite + Tailwind v4 (chosen for the spec's recommended stack).
Design brief: this is an internal ops tool, not a marketing page, so the
direction was functional-but-considered rather than flashy — a warm-neutral
canvas, a deep teal-green accent (deliberately avoiding the generic
cream/terracotta and near-black/acid-green looks that AI tools default to),
Space Grotesk for headers, Inter for body, IBM Plex Mono for seat codes.
Four screens: Dashboard (KPIs + floor/project utilization), Employees
(search + allocate/release), Floor Map (the signature element — a literal
color-coded seat grid per floor/zone, since the subject is physical office
seating), and Assistant (chat UI over `/ai/query`).

## Prompt 7 – Testing

Claude ran the app for real inside the sandbox rather than only
eyeballing the code:
- `python -m app.seed` and verified the printed counts matched every seed
  target in the spec (5,500 seats, 5,000 employees, 500 available, 120
  reserved, ~150 pending).
- Started `uvicorn` and used `curl` against every endpoint (employees CRUD +
  search + duplicate-email/seat rejection, projects, seats + filters,
  `/dashboard/*`, `/seats/allocate` + `/release` full cycle, and `/ai/query`)
  with the exact example questions from the spec.
- Ran `npm run build` on the frontend to catch compile errors, then booted
  backend + `vite preview` together and confirmed the frontend's origin
  gets a valid CORS response (`access-control-allow-origin` header present)
  from the API, and inspected the compiled CSS to confirm the custom
  Tailwind theme tokens (brand color, status colors, fonts) actually
  generated real utility classes rather than silently falling back to
  defaults.

## Prompt 8 – Debugging

Issues Claude generated incorrectly, and how they were found/fixed:

1. **Missing `email-validator` dependency** — Pydantic's `EmailStr` type
   raised `ImportError` on server start. Found via the uvicorn crash log,
   fixed by installing `email-validator` and pinning `pydantic[email]` in
   `requirements.txt`.
2. **Background server dying between shell calls** — first attempts to run
   `uvicorn &` in one command and `curl` it in a later command failed
   (`Connection refused`) because each tool invocation tears down background
   processes. Fixed by starting the server and running all curl checks
   within a single shell session.
3. **AI assistant name-extraction regex too greedy** — `"Where is employee
   Cheryl Avila seated?"` initially failed to match because the regex
   captured `"Cheryl Avila seated"` as the name (including the trailing
   verb), so the DB lookup found no employee. Fixed with a lookahead that
   stops the capture before `is/seated/sit/located` or `?`.
4. **"Which project is X assigned to?" phrasing not handled** — the original
   regex only looked for `"employee <name>"`, which this phrasing doesn't
   use. Added a second regex (`"is <name> assigned"`) as a fallback.
5. **Dead/no-op code branch** left in `dashboard.py` from an initial
   DB-dialect-dependent approach to floor utilization (`.cast()` isn't
   portable across SQLite/Postgres) — removed in favor of a simple
   per-floor `COUNT` loop that works on any backend.
6. **Tailwind v4 arbitrary grid columns** — `grid-cols-14` / `grid-cols-16`
   aren't real Tailwind utilities (default scale stops at 12); the seat
   grid silently would have fallen back to no column rule. Fixed by using
   bracket syntax (`grid-cols-[repeat(16,minmax(0,1fr))]`).
7. **Invalid `font-700` class** in the sidebar — Tailwind font-weight
   utilities are named (`font-semibold`), not numeric; fixed before it ever
   reached a build.

## Prompt 9 – Deployment

Not yet done. Documented as a next step; recommended targets from the spec
(Railway/Render) are ready to receive this app as-is once `DATABASE_URL` is
pointed at a managed Postgres instance.

## Prompt 10 – Refactoring

Kept intentionally minimal for a first working pass: one concern (CRUD,
allocation, dashboard, AI) per router file, schemas separated from models,
seed data isolated in its own script so it never runs as a side effect of
importing the app.

## What AI generated correctly

- All CRUD endpoints matching the spec's exact paths/methods on first pass.
- Seed data generator hit every numeric target in the spec exactly
  (verified by direct run, not assumed).
- Core business rules (no duplicate seat/email, one active allocation per
  employee, released seat returns to available) worked correctly on first
  functional test.

## What AI generated incorrectly

- The email dependency, the two regex bugs above, and the dead code branch
  in `dashboard.py` (all listed under Prompt 8).

## How correctness was verified

Not just code review — every core flow was actually executed in the sandbox:
seed script run and counts checked against the spec's numeric requirements;
server booted and hit with real `curl` requests for every endpoint category
(CRUD, search, filters, duplicate-rejection, seat allocate/release full
cycle, all AI assistant example queries from the spec) with responses
inspected for correctness; frontend built with `npm run build` and served
alongside the live backend to confirm CORS and real network calls work
end-to-end, not just that the components render in isolation.
