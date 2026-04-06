# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

P003-Whatever is an AI-powered "nearby destination decision-maker" PWA. Users describe their mood/budget/commute, and the system recommends a nearby place to go. Built with FastAPI backend + React/Vite frontend.

## Dev Commands

### Backend
```bash
cd backend
source .venv/bin/activate          # activate virtualenv (create with: python -m venv .venv)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd UIUX
npm install
npm run dev      # starts at :5173, proxies /api → http://localhost:8000
npm run build
npm run lint
```

Normal dev: run backend on terminal 1, frontend on terminal 2. Browse at http://localhost:5173.

## Architecture

**API flow (6 endpoints under `/api/v1`):**
1. `POST /recommend/init` — parse user prompt → create session, return `session_id`
2. `POST /recommend/candidates` — call Amap API → score POIs → return top-5
3. `POST /recommend/pick` — weighted random selection → return 1 final + 2 alternatives
4. `POST /persona/review` — template-based persona commentary (4 personas)
5. `POST /feedback/submit` — save satisfaction + actual cost
6. `GET /history/list` — paginated history

**Backend structure (`backend/app/`):**
- `main.py` — FastAPI app, CORS, mounts router at `/api/v1`
- `routes.py` — all 6 endpoints; handles scoring, fallback mock data, debug headers
- `db.py` — SQLite (3 tables: `sessions`, `picks`, `history`)
- `services/intent_parser.py` — rule-based NLU: maps user keywords → Amap type codes + radius
- `services/amap.py` — Amap POI search, reverse geocoding, nav URL generation

**Frontend structure (`UIUX/src/`):**
- React 18 + React Router 7 + Tailwind 4 + Radix UI + MUI
- `app/App.tsx` + `app/routes.tsx` — router root and route definitions
- `app/pages/` — page components (home, candidates, result, feedback, history, dashboard)
- `app/components/` — reusable UI: `candidate-card`, `persona-tabs`, `location-bar`, etc.
- Vite proxies `/api` to backend in dev; configure `vite.config.ts` for production base URL

**Scoring logic (in `routes.py`):**
- Distance: up to −40% penalty as distance → radius limit
- Rating: +15% bonus from Amap rating
- Budget: hard 0-score filter if over limit
- Type diversity: cap at 2 POIs per category
- ±8% random noise for variety
- Weighted random pick (not deterministic top-1)

**LLM integration:** `services/llm.py` calls DeepSeek API (OpenAI-compatible) for pick reasons and persona reviews. Requires `DEEPSEEK_API_KEY`. Falls back to default copy / template personas on failure — never blocks the user flow.

## Key Config

- `backend/.env` — required: `AMAP_KEY`, `DEEPSEEK_API_KEY`; see `.env.example` for full list
- Production DB: `DATABASE_URL` (PostgreSQL on Render); local dev: SQLite at `DB_PATH` (default `/tmp/p003.db`)
- `.claude/settings.local.json` — allows `Bash(npm run:*)`
- Vite proxy in `vite.config.ts`: `/api` → `http://localhost:8000`
- `configs/ranking-config.json` — scoring weights (edit here, not in `routes.py`)

## Standard Response Envelope

```json
{ "code": "OK|INVALID_PARAMS|UPSTREAM_TIMEOUT|...", "message": "...", "data": {}, "fallback_used": false }
```

## Deployment

- **Backend → Render** (`render.yaml`): `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Frontend → Vercel** (`vercel.json`): builds `UIUX/`, rewrites all routes to `index.html`
- Health check: `GET /health` (used by Render)

## Debug / Testing

- Pass `X-Debug-Scenario` header to trigger error states in routes
- API contract and schema documented in `docs/api-contract.md` and `docs/data-schema.md`
- Orchestrator state machine documented in `docs/orchestrator-flow.md`
