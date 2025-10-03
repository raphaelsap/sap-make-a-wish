# SAP BTP - Make a Wish

Perplexity-powered Streamlit workspace that drafts SAP Joule agents end-to-end. Provide a customer scenario, let Perplexity assemble the prompt, schema, business case, and tables, then push the payload directly to the SAP Agents service.

## Getting Started

### Streamlit app
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```
The UI runs at <http://localhost:8501> by default.

### Optional FastAPI backend
If you need the SAP HANA bootstrap utilities, start the backend separately:
```bash
pip install -r server/requirements.txt
uvicorn server.app:app --reload --port 8000
```

## Environment Variables
Set these in your shell or a `.env` file before launching Streamlit:

- `PPLX_API_KEY` — Perplexity API key used to generate the agent proposal.
- `PPLX_MODEL` *(optional)* — Override for the Perplexity model (default `sonar`).
- `SAP_AGENT_BASE_URL` — Base URL for the SAP Agents REST API.
- `SAP_AGENT_OAUTH_URL` — OAuth token endpoint.
- `SAP_AGENT_CLIENT_ID` / `SAP_AGENT_CLIENT_SECRET` — Credentials for `sap_agents_api.py`.
- `SAP_AGENT_UI_BASE_URL` *(optional)* — Used for deep links after creation.
- `BACKEND_AGENT_ENDPOINT` — URL to the FastAPI endpoint that provisions HANA and calls SAP Agents (default `http://localhost:8000/api/agents`).
- `HANA_*` — Required only when the FastAPI backend provisions SAP HANA assets.

> ⚠️ Keep secrets out of version control. `.env` is ignored by git.

## Using the app
1. Enter the customer name and use case, then click **Generate with Perplexity**.
2. Review the returned agent name, prompt, business case card, and tables.
3. When satisfied, press **Generate agent** to invoke the SAP Agents API.
4. Inspect the JSON payload inside the expandable section if you need to reuse it elsewhere.

## Deploying to SAP BTP Cloud Foundry
1. Log in to your Cloud Foundry org/space and target the desired space:
   ```bash
   cf login --sso
   cf target -o <org> -s <space>
   ```
2. Provide the required secrets. Either create a user-provided service or set them directly as app env vars, for example:
   ```bash
   cf set-env sap-btp-make-a-wish PPLX_API_KEY <your-perplexity-key>
   cf set-env sap-btp-make-a-wish SAP_AGENT_BASE_URL <sap-agent-base-url>
   cf set-env sap-btp-make-a-wish SAP_AGENT_OAUTH_URL <sap-agent-oauth-url>
   cf set-env sap-btp-make-a-wish SAP_AGENT_CLIENT_ID <client-id>
   cf set-env sap-btp-make-a-wish SAP_AGENT_CLIENT_SECRET <client-secret>
   ```
   Repeat for any additional variables (e.g., `SAP_AGENT_UI_BASE_URL`).
3. Push the Streamlit app using the included `manifest.yml` (add `--random-route` if you need a unique hostname):
   ```bash
   cf push --random-route
   ```
   The `python_buildpack` installs everything from `requirements.txt`, then `start.sh` launches Streamlit bound to the platform-provided `$PORT`.
4. After the deployment completes, retrieve the route with `cf apps` and open it in your browser.

## Repository layout
- `streamlit_app.py` — Streamlit front end that calls Perplexity and the SAP Agents API.
- `sap_agents_api.py` — Lightweight SAP Agents client shared by the app and backend.
- `server/` — Optional FastAPI utilities for SAP HANA orchestration.

Enjoy crafting SAP Joule experiences! ✨
