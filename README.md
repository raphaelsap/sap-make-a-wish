# SAP Joule Make A Wish

Modern Vite + React + Tailwind UI coupled with a FastAPI backend that orchestrates SAP Joule demo agents. The flow:

1. Enter a customer and use case.
2. Frontend calls Perplexity (via `VITE_PPLX_API_KEY`) to generate the agent name, prompt, SAP HANA schema, ten tables (columns + sample rows), and business case narrative.
3. Press **Create and open in SAP Joule** to persist everything in SAP HANA Cloud and create the agent in the SAP Agents workspace.
4. The app opens the SAP Joule console for the freshly minted agent.

## Getting Started

### Frontend
```bash
npm install
npm run dev
```

### Backend (FastAPI)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.app:app --reload --port 8000
```

The Vite dev server proxies `/api/*` calls to `http://localhost:8000`.

## Environment Variables
Copy `.env.example` to `.env` and adjust as needed.

- `VITE_PPLX_API_KEY` — Perplexity API key used by the frontend.
- `HANA_*` — SAP HANA Cloud connection for catalog + per-use-case schemas.
- `SAP_AGENT_*` — OAuth client credentials and endpoints for the SAP Agents API.
- `PPLX_API_KEY_ALIAS` — Alias registered in the SAP Agents workspace for the Perplexity key.

> ⚠️ Handle credentials securely and rotate frequently. The `.gitignore` excludes `.env` from source control.

## Agent Metadata Storage
- `AGENT_CATALOG.AGENTS` tracks every agent (name, customer, use case, schema, Joule prompt, business case).
- `AGENT_CATALOG.AGENT_ASSETS` records the ten curated tables + column metadata per agent.
- Each use case receives its own schema (e.g., `JOULE_CUSTOMER_USECASE`) populated with the Perplexity-generated tables and sample rows.

## SAP Agents Integration
The backend imports `PostAgentsAPI` from `sap_agents_api.py` to create agents in `https://agents-y0yj1uar`. Returned agent IDs feed the Joule UI deep link, which the frontend opens in a new tab upon success.

## Health Check
`GET /healthz` returns `{ "status": "ok" }` to assist with deployment probes.

Enjoy crafting Joule-powered demo packages! ✨
