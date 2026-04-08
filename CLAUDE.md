# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

P003-Whatever is an AI-powered "nearby destination decision-maker" PWA. Users describe their mood/budget/commute, and the system recommends a nearby place to go. Built with FastAPI backend + React/Vite frontend, deployed on Render (backend) + Vercel (frontend).

**Current version: v0.6** — Celebrity PRO personas live, LLM intent parsing active, share card built.

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

**API flow (8 endpoints under `/api/v1`):**
1. `POST /auth/anonymous` — create/reuse anonymous user identity (cookie-based)
2. `POST /recommend/init` — LLM intent parse → create session, return `session_id` + `address_name`
3. `POST /recommend/candidates` — Amap POI search → score → return top-5 with AI judgements
4. `POST /recommend/pick` — weighted random selection → return 1 final + 2 alternatives
5. `POST /persona/review` — LLM persona/celebrity review → 4-slice structured output
6. `POST /feedback/submit` — save satisfaction + actual cost
7. `GET /history/list` — paginated history
8. `GET /static-map` — proxy Amap static map image (hides API key)

**Backend structure (`backend/app/`):**
- `main.py` — FastAPI app, CORS, mounts router at `/api/v1`
- `routes.py` — all endpoints; scoring logic, concurrent async calls, fallback mock data, debug headers
- `db.py` — SQLite (local) / PostgreSQL (prod), 3 tables: `sessions`, `picks`, `history`
- `services/intent_parser.py` — rule-based NLU fallback: maps keywords → Amap type codes + radius
- `services/llm.py` — DeepSeek LLM client: intent parsing, pick reasons, persona reviews, celebrity reviews, inspire, search summary
- `services/amap.py` — Amap POI search, reverse geocoding, weather, static map, nav URL
- `skills/jobs.skill` — Steve Jobs celebrity persona (YAML-frontmatter skill file)

**Frontend structure (`UIUX/src/`):**
- React 18 + React Router 7 + Tailwind 4 + Radix UI + MUI
- `app/App.tsx` + `app/routes.tsx` — router root and route definitions
- `app/pages/` — home, candidates, result, feedback, history, dashboard
- `app/components/` — candidate-card, persona-tabs, location-bar, PersonaSliceView, ShareCardNode, CelebrityPersonaCard, ProGateSheet
- `app/lib/celebrities.ts` — celebrity constants + `isPro()` / `setPro()` (localStorage-based, beta always returns true)

**LLM integration (`services/llm.py`):**
- `parse_intent_with_ai()` — multi-category intent with weights + time context; falls back to `intent_parser.py` on failure
- `pick_reason()` — 命运独白 for each candidate card (timeout 5s, temperature 0.95)
- `persona_review()` — 4-scene slice output + summary (timeout 9s, max_tokens 500)
- `celebrity_persona_review()` — loads `.skill` file as system prompt, outputs verdict field (timeout 22s, max_tokens 1500)
- `generate_inspire()` — home page "AI帮我想一个" (timeout 6s, temperature 1.1); pre-fetched on page load
- `generate_search_summary()` — candidates page header copy (timeout 5s)
- All `json.loads()` wrapped in try/except; all functions have explicit timeout params
- Falls back gracefully on any LLM failure — never blocks user flow

**Scoring logic (`routes.py → _score_poi()`):**
- Distance: up to −40% penalty as distance → radius limit
- Rating: +15% bonus from Amap rating
- Budget: hard 0-score filter if over limit
- Type diversity: cap at 2 POIs per category
- Type weights: `+0.07` boost for `preferred_category` from LLM intent
- Wild Card: one low-score POI randomly promoted for serendipity
- ±8% random noise; weighted random pick (not deterministic top-1)

**Concurrency in `recommend_init`:**
- GPS path: `asyncio.gather(parse_intent_with_ai, regeo_with_adcode)` → then `get_weather_by_adcode` (~2s)
- Text address path: `asyncio.gather(parse_intent_with_ai, geocode)` → then `asyncio.gather(regeo, weather)` (~2.5s)

## Key Config

- `backend/.env` — required: `AMAP_KEY`, `DEEPSEEK_API_KEY`; see `.env.example` for full list
- Production DB: `DATABASE_URL` (PostgreSQL on Render); local dev: SQLite at `DB_PATH` (default `/tmp/p003.db`)
- Vite proxy in `vite.config.ts`: `/api` → `http://localhost:8000`
- `configs/ranking-config.json` — scoring weights (edit here, not in `routes.py`)

## Standard Response Envelope

```json
{ "code": "OK|INVALID_PARAMS|UPSTREAM_TIMEOUT|...", "message": "...", "data": {}, "fallback_used": false }
```

## Persona / Celebrity Review Response Shape

```json
{
  "persona": "独处型",
  "summary": "一句话结论 ≤20字",
  "slices": [
    { "scene": "to_door", "tag": "到门口", "text": "...", "emotion": "..." },
    { "scene": "enter",   "tag": "进入后", "text": "...", "emotion": "..." },
    { "scene": "during",  "tag": "体验中", "text": "...", "emotion": "..." },
    { "scene": "leave",   "tag": "总结",   "text": "...", "emotion": "..." }
  ],
  "verdict": "辣评一句，仅 celebrity 模式有值",
  "review": "...",
  "risk": "...",
  "conclusion": "...",
  "fallback_used": false
}
```

## Deployment

- **Backend → Render** (auto-deploy on push to `main`): `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Frontend → Vercel** (`vercel.json`): builds `UIUX/`, rewrites all routes to `index.html`
- Health check: `GET /health` (used by Render)
- Service ID: `srv-d6vo579r0fns73cdi9n0`

## Debug / Testing

- Pass `X-Debug-Scenario` header to trigger error states in routes
- API contract and schema documented in `docs/api-contract.md` and `docs/data-schema.md`
- Orchestrator state machine documented in `docs/orchestrator-flow.md`
- Celebrity skills in `backend/app/skills/*.skill` (YAML frontmatter stripped at load time)
