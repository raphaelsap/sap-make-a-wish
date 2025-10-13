"""Streamlit app for generating SAP Joule agents via Perplexity."""

from __future__ import annotations

import json
import os
import uuid
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

from dotenv import load_dotenv
load_dotenv()

from markdown import markdown
from sap_agents_api import SAPAgentAPIError, create_agent_tool, list_agents
from server.app import (
    TableDefinition,
    create_schema_with_tables,
    ensure_catalog,
    hana_connect,
    register_agent_metadata,
    sanitize_identifier,
)


PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_PPLX_MODEL = os.getenv("PPLX_MODEL", "sonar")
PROMPT_FILE = Path(__file__).parent / "prompts" / "perplexity.md"
SAP_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/5/59/SAP_2011_logo.svg"
SAP_AGENT_UI_URL = "https://agents-y0yj1uar.baf-dev.cfapps.eu12.hana.ondemand.com/ui/index.html#/agents"


def inject_global_styles() -> None:
    """Inject custom CSS for the streamlined workspace aesthetic."""

    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap');

            html, body, [data-testid="stAppViewContainer"] {
                font-family: 'Manrope', sans-serif;
                background: radial-gradient(circle at 20% 20%, rgba(28, 35, 52, 0.6), transparent 55%),
                            radial-gradient(circle at 80% 15%, rgba(22, 27, 41, 0.5), transparent 60%),
                            linear-gradient(135deg, #0b1220 0%, #0e1426 50%, #121a2e 100%);
                color: #ffffff;
            }
            body * {
                color: #ffffff !important;
            }

            [data-testid="stHeader"] { display: none; }

            [data-testid="stAppViewContainer"] > .main {
                padding: 0 3rem 4rem;
            }

            .block-container {
                padding-top: 0 !important;
            }

            .app-banner {
                display: flex;
                align-items: center;
                gap: 1rem;
                margin: 2.2rem 0 1.2rem;
            }

            .app-banner__tagline {
                font-weight: 600;
                color: #ffffff;
            }

            [data-testid="stForm"] {
                background: rgba(16, 20, 30, 0.92);
                border-radius: 28px;
                border: 1px solid rgba(116, 88, 255, 0.18);
                padding: 2.4rem 2.6rem;
                box-shadow: 0 24px 64px rgba(68, 32, 153, 0.12);
                backdrop-filter: blur(24px);
            }

            [data-testid="stForm"] label {
                font-weight: 600;
                color: #ffffff;
            }

            div[data-baseweb="input"] > div > input,
            [data-baseweb="textarea"] textarea {
                border-radius: 16px !important;
                border: 1px solid rgba(125, 88, 255, 0.22) !important;
                background: rgba(22, 26, 36, 0.92) !important;
                box-shadow: inset 0 1px 2px rgba(82, 40, 160, 0.08) !important;
                color: #ffffff !important;
            }
            div[data-baseweb="input"] > div > input::placeholder,
            [data-baseweb="textarea"] textarea::placeholder {
                color: #ffffff !important;
                opacity: 1 !important;
            }

            div[data-baseweb="input"] > div > input:focus,
            [data-baseweb="textarea"] textarea:focus {
                border-color: rgba(111, 76, 250, 0.65) !important;
                box-shadow: 0 0 0 3px rgba(111, 76, 250, 0.18) !important;
            }

            [data-testid="baseButton-primary"] {
                background: linear-gradient(120deg, #6f4cfa, #af59ff) !important;
                border: none !important;
                box-shadow: 0 18px 38px rgba(111, 76, 250, 0.28) !important;
                border-radius: 999px !important;
                font-weight: 700 !important;
                padding: 0.7rem 1.8rem !important;
                color: #ffffff !important;
            }

            [data-testid="baseButton-secondary"] {
                background: rgba(255, 255, 255, 0.8) !important;
                color: #ffffff !important;
                border: 1px solid rgba(125, 88, 255, 0.22) !important;
                border-radius: 999px !important;
                font-weight: 700 !important;
                padding: 0.7rem 1.8rem !important;
                box-shadow: 0 16px 30px rgba(128, 96, 255, 0.16) !important;
            }

            [data-testid="metric-container"] {
                background: rgba(18, 22, 32, 0.9);
                border-radius: 20px;
                border: 1px solid rgba(118, 88, 255, 0.18);
                box-shadow: 0 18px 42px rgba(80, 40, 160, 0.14);
                padding: 1.2rem 1.5rem;
                color: #ffffff;
            }

            [data-testid="stExpander"] {
                background: rgba(18, 22, 32, 0.9);
                border-radius: 20px !important;
                border: 1px solid rgba(116, 88, 255, 0.18);
                box-shadow: 0 18px 36px rgba(68, 30, 148, 0.14) !important;
                color: #ffffff;
            }

            @media (max-width: 900px) {
                [data-testid="stAppViewContainer"] > .main {
                    padding: 0 1.5rem 3rem;
                }

                .app-banner {
                    flex-direction: column;
                    align-items: flex-start;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def load_prompt_sections() -> Dict[str, str]:
    text = PROMPT_FILE.read_text(encoding="utf-8")
    system_marker = "## System Instruction"
    user_marker = "## User Template"

    system_part = ""
    user_part = ""

    if system_marker in text and user_marker in text:
        _, rest = text.split(system_marker, 1)
        system_part, user_part = rest.split(user_marker, 1)
    else:
        raise RuntimeError("Prompt file missing required sections")

    return {
        "system": system_part.strip(),
        "user": user_part.strip(),
    }


def strip_code_fences(content: str) -> str:
    trimmed = content.strip()
    if trimmed.startswith("```"):
        trimmed = trimmed.split("\n", 1)[-1]
        if trimmed.endswith("```"):
            trimmed = trimmed.rsplit("```", 1)[0]
    return trimmed.strip()


def parse_llm_payload(content: str) -> Dict[str, Any]:
    cleaned = strip_code_fences(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced via UI
        raise ValueError("Perplexity response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Perplexity response must be a JSON object")

    tables = parsed.get("tables")
    if not isinstance(tables, list) or not tables:
        raise ValueError("Perplexity response missing tables array")

    return parsed


def build_messages(
    customer: str,
    use_case: str,
    main_solution: str = "",
    metric: str = "",
    refinements: Optional[str] = None,
    current_fields: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    prompt_sections = load_prompt_sections()
    system_instruction = prompt_sections["system"]

    scenario_lines = [
        f"Customer: {customer}",
        f"Use case: {use_case}",
        f"Main SAP solution focus: {main_solution or 'Not specified'}",
        f"Metric to optimise: {metric or 'Not specified'}",
    ]

    if current_fields:
        context_lines = []
        for label, value in current_fields.items():
            if value:
                context_lines.append(f"{label}: {value}")
        if context_lines:
            scenario_lines.append(
                "Current agent configuration to keep aligned (update only if improvements are suggested):\n"
                + "\n".join(context_lines)
            )

    if refinements and refinements.strip():
        scenario_lines.append(f"Refinement requests: {refinements.strip()}")

    scenario_lines.append(
        "Return at least 6 imagined SAP-relevant tables (conceptual, not from any live database) covering data sources, KPIs, and enablement assets. "
        "Do not query or rely on external databases (e.g., HANA); instead, propose plausible columns and include 1–2 illustrative sample rows. "
        "Provide a compelling agentName and a businessCaseCard string with emoji headers (Problem, Solution, Benefits, ROI)."
    )

    scenario = "\n".join(scenario_lines)
    user_template = prompt_sections["user"].replace("{customer}", customer)
    user_template = user_template.replace("{use_case}", use_case)
    user_template = user_template.replace("{main_solution}", main_solution or "Not specified")
    user_template = user_template.replace("{metric}", metric or "Not specified")

    if current_fields:
        current_text = "\n" + "\n".join(
            f"{key}: {value}" for key, value in current_fields.items() if value
        )
    else:
        current_text = ""
    user_template = user_template.replace("{current_fields}", current_text)
    user_template = user_template.replace("{refinements}", refinements.strip() if refinements else "")

    return [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_template + "\n" + scenario},
    ]


def request_demo_package(
    customer: str,
    use_case: str,
    main_solution: str = "",
    metric: str = "",
    refinements: Optional[str] = None,
    current_fields: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    api_key = os.getenv("PPLX_API_KEY")
    if not api_key:
        raise RuntimeError("Set PPLX_API_KEY in your environment to call Perplexity.")

    payload = {
        "model": DEFAULT_PPLX_MODEL,
        "messages": build_messages(customer, use_case, main_solution, metric, refinements, current_fields),
        "max_tokens": 4096,
        "temperature": 0.15,
    }

    response = requests.post(
        PPLX_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Perplexity API error {response.status_code}: {response.text}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover
        raise RuntimeError("Unexpected Perplexity response shape") from exc

    return parse_llm_payload(content)


def display_tables(tables: List[Dict[str, Any]]) -> None:
    st.markdown("**📊 Tables prepared by SAP Joule**")
    for table in tables:
        name = table.get("name", "Unnamed table")
        columns = table.get("columns", [])
        rows = table.get("rows", [])
        with st.expander(
            f"{name} · {len(columns)} columns · {len(rows)} sample rows",
            expanded=False,
        ):
            if table.get("desc"):
                st.write(table["desc"])

            grid = [
                {
                    "Column": col.get("name", ""),
                    "Type": col.get("type", ""),
                    "Nullable": "Yes" if col.get("nullable", True) else "No",
                    "Primary Key": "Yes" if col.get("isPrimaryKey") else "No",
                    "Description": col.get("description", "—"),
                }
                for col in columns
            ]
            if grid:
                st.table(grid)
            else:
                st.info("No column metadata provided.")

            if rows:
                st.markdown("**Sample rows**")
                st.json(rows)


def render_holographic_card(content: str) -> None:
    html_content = markdown(content or "", extensions=["extra"]) or ""
    st.markdown(
        f"""
        <style>
            @keyframes holo-rotate {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .holo-card {{
                position: relative;
                padding: 1.6rem;
                border-radius: 1.35rem;
                background: radial-gradient(circle at 20% 20%, rgba(59,130,246,0.35), rgba(236,72,153,0.25)),
                            linear-gradient(135deg, rgba(16,185,129,0.25), rgba(129,140,248,0.2));
                box-shadow: 0 25px 60px rgba(15,23,42,0.45);
                overflow: hidden;
                border: 1px solid rgba(148,163,184,0.3);
            }}
            .holo-card::before {{
                content: "";
                position: absolute;
                inset: -60%;
                background: conic-gradient(from 180deg at 50% 50%, rgba(56,189,248,0.55), rgba(236,72,153,0.65), rgba(249,115,22,0.55), rgba(56,189,248,0.55));
                animation: holo-rotate 10s linear infinite;
                opacity: 0.6;
            }}
            .holo-card::after {{
                content: "";
                position: absolute;
                inset: 1.5px;
                border-radius: 1.25rem;
                background: rgba(15,23,42,0.86);
                backdrop-filter: blur(14px);
            }}
            .holo-content {{
                position: relative;
                z-index: 1;
                white-space: pre-wrap;
                line-height: 1.55;
                font-size: 0.95rem;
                font-family: 'Inter', sans-serif;
                color: #ffffff;
                text-shadow: 0 0 14px rgba(59,130,246,0.35);
            }}
        </style>
        <div class="holo-card"><div class="holo-content">{html_content}</div></div>
        """,
        unsafe_allow_html=True,
    )


def build_default_tool_payloads() -> List[Dict[str, Any]]:
    """Return a single Perplexity tool payload.

    - Tool: type 'bringyourown', config uses {'name': 'destination', 'value': <env or 'perplexity'>}
    """
    p_value = os.getenv("PPLX_DESTINATION", "perplexity").strip() or "perplexity"
    return [
        {
            "name": "Perplexity Destination",
            "type": "bringyourown",
            "config": [
                {"name": "destination", "value": p_value},
            ],
        }
    ]


def provision_agent_tools(agent_id: str) -> List[Dict[str, Any]]:
    """Create the default tool set for the specified agent, with fallback schema if the primary payload fails.

    Primary payload uses config name 'perplexity'. If the landscape rejects it, we retry with 'destination'.
    Returns tool summaries including raw API responses.
    """
    created_tools: List[Dict[str, Any]] = []
    for payload in build_default_tool_payloads():
        try:
            res = create_agent_tool(agent_id, payload)
            created_tools.append(
                {
                    "name": payload.get("name", "Unnamed tool"),
                    "type": payload.get("type", ""),
                    "response": res,
                }
            )
        except SAPAgentAPIError as exc:
            # Fallback to alternate schema using 'destination' key
            # Carry forward the value from the original payload's config if present, else default to 'perplexity'
            cfg_list = payload.get("config") or []
            dest_val = "perplexity"
            for entry in cfg_list:
                if isinstance(entry, dict) and entry.get("name") in ("perplexity", "destination"):
                    dest_val = str(entry.get("value", "perplexity")) or "perplexity"
                    break
            alt_payload: Dict[str, Any] = {
                "name": "Web Search Tool",
                "type": payload.get("type", "bringyourown"),
                "config": [{"name": "perplexity", "value": dest_val}],
            }
            try:
                alt_res = create_agent_tool(agent_id, alt_payload)
                created_tools.append(
                    {
                        "name": alt_payload.get("name", "Web Search Tool"),
                        "type": alt_payload.get("type", ""),
                        "response": alt_res,
                        "fallbackFrom": payload.get("name", "Unnamed tool"),
                        "error": str(exc),
                    }
                )
            except SAPAgentAPIError as exc2:
                created_tools.append(
                    {
                        "name": payload.get("name", "Unnamed tool"),
                        "type": payload.get("type", ""),
                        "response": {"error": str(exc2), "status": getattr(exc2, "status_code", None)},
                        "failed": True,
                    }
                )
    return created_tools


def build_agent_payload(package: Dict[str, Any], customer: str, use_case: str) -> Dict[str, Any]:
    agent_name = st.session_state.get("agent_name_edit") or package.get("agentName", "SAP Joule Agent")
    agent_prompt = st.session_state.get("agent_prompt_edit") or package.get("agentPrompt", "")
    schema_name = st.session_state.get("schema_name_edit") or package.get("schemaName", "JOULE_DEMO_SCHEMA")
    business_case = st.session_state.get("business_case_card_edit") or package.get("businessCaseCard", "")

    return {
        "name": agent_name.strip(),
        "prompt": agent_prompt.strip(),
        "customer": customer.strip(),
        "useCase": use_case.strip(),
        "schemaName": schema_name.strip() or "JOULE_DEMO_SCHEMA",
        "tables": package.get("tables", []),
        "businessCaseCard": business_case,
    }


def regenerate_proposal(refinement_text: str) -> None:
    try:
        package = request_demo_package(
            st.session_state.get("customer", ""),
            st.session_state.get("use_case", ""),
            st.session_state.get("main_solution", ""),
            st.session_state.get("metric", ""),
            refinements=refinement_text,
            current_fields={
                "Agent name": st.session_state.get("agent_name_edit", ""),
                "Schema name": st.session_state.get("schema_name_edit", ""),
                "Agent prompt": st.session_state.get("agent_prompt_edit", ""),
            },
        )
    except Exception as exc:  # pragma: no cover
        st.error(f"Unable to regenerate the proposal: {exc}")
    else:
        st.session_state["demo_package"] = package
        st.session_state["agent_name_edit"] = package.get("agentName", "")
        st.session_state["schema_name_edit"] = package.get("schemaName", "")
        st.session_state["agent_prompt_edit"] = package.get("agentPrompt", "")
        st.session_state["business_case_card_edit"] = package.get("businessCaseCard", "")
        st.success("Updated proposal received. Review the refreshed details above.")


def streamlit_app() -> None:
    st.set_page_config(page_title="SAP BTP - Make a Wish", layout="wide")
    inject_global_styles()

    sap_defaults = {
        "sap_agent_name": "Web Search Expert",
        "sap_agent_expert_in": "You are an expert in searching the web",
        "sap_agent_instructions": "## WebSearch Tool Hint\nTry to append 'Wikipedia' to your search query",
    }
    for key, value in sap_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "agent_tools" not in st.session_state:
        st.session_state["agent_tools"] = []

    st.markdown(
        f'''
        <div class="app-banner">
          <img src="{SAP_LOGO_URL}" alt="SAP" style="height: 48px;" />
          <h1 style="margin: 0;">Joule + BTP = Make a Wish ✨</h1>
        </div>
        ''',
        unsafe_allow_html=True,
    )



    with st.form("scenario-form"):
        customer = st.text_input("👤 Customer name", value=st.session_state.get("customer", ""))
        use_case_col, solution_col = st.columns((2, 1))
        with use_case_col:
            use_case = st.text_area(
                "🧭 Use case",
                value=st.session_state.get("use_case", ""),
                placeholder="Describe the outcome, scope, and SAP capabilities to highlight.",
            )
        with solution_col:
            main_solution = st.text_input(
                "💡 Main SAP solution",
                value=st.session_state.get("main_solution", ""),
                placeholder="e.g. SAP S/4HANA, SAP Datasphere",
            )
        metric = st.text_input(
            "📈 Metric for the agent to optimise",
            value=st.session_state.get("metric", ""),
            placeholder="e.g. Net revenue retention, Time-to-value, Customer adoption score",
        )
        submitted = st.form_submit_button("Generate Joule Agent 🚀")

    if submitted:
        if not customer.strip() or not use_case.strip():
            st.error("Please provide both a customer name and use case before generating.")
        else:
            with st.spinner("Calling AI to assemble the SAP Joule proposal…"):
                try:
                    package = request_demo_package(customer, use_case, main_solution, metric)
                except Exception as exc:  # pragma: no cover - surfaced to UI
                    st.session_state.pop("demo_package", None)
                    st.error(f"Unable to generate the proposal: {exc}")
                else:
                    st.session_state["demo_package"] = package
                    st.session_state["customer"] = customer.strip()
                    st.session_state["use_case"] = use_case.strip()
                    st.session_state["main_solution"] = main_solution.strip()
                    st.session_state["metric"] = metric.strip()
                    st.session_state["agent_name_edit"] = package.get("agentName", "")
                    st.session_state["schema_name_edit"] = package.get("schemaName", "")
                    st.session_state["agent_prompt_edit"] = package.get("agentPrompt", "")
                    st.session_state["business_case_card_edit"] = package.get("businessCaseCard", "")
                    st.session_state["sap_agent_name"] = package.get("agentName", st.session_state.get("sap_agent_name", "Web Search Expert"))
                    st.session_state["sap_agent_instructions"] = package.get("agentPrompt", st.session_state.get("sap_agent_instructions", ""))
                    st.session_state["sap_agent_expert_in"] = (
                        f"You are an expert in {main_solution or use_case}"
                        if (main_solution or use_case)
                        else st.session_state.get("sap_agent_expert_in", "You are an expert in searching the web")
                    )
                    st.session_state.pop("agent_success", None)
                    st.session_state.pop("agent_error", None)
                    st.success("Response received. Review the proposal below.")

    package = st.session_state.get("demo_package")
    if not package:
        #st.info("Enter scenario details above and click Generate to see the SAP Joule proposal.")
        return

    st.divider()
    st.subheader("SAP Joule proposal 🪄")

    st.text_input("Agent name", key="agent_name_edit")

    st.markdown("**🎴 Business case**")
    render_holographic_card(st.session_state.get("business_case_card_edit", ""))


    tables = package.get("tables", [])
    if tables:
        display_tables(tables)
    else:
        st.warning("No tables returned for this scenario.")
    """
    st.divider()
    st.subheader("Iterate on the proposal 🔁")
    st.text_area(
        "Adjustments or change requests",
        key="refinement_text",
        placeholder="Add adjustments",
        height=100,
    )

    if st.button("✨ Regenerate with adjustments", type="secondary"):
        refinement_text = st.session_state.get("refinement_text", "")
        if not refinement_text.strip():
            st.warning("Enter some refinement instructions before regenerating.")
        else:
            with st.spinner("Revising proposal..."):
                regenerate_proposal(refinement_text)
    """
    st.divider()
    st.subheader("Create the SAP agent ✅")

    payload = build_agent_payload(
        package,
        st.session_state.get("customer", ""),
        st.session_state.get("use_case", ""),
    )

    button_cols = st.columns((1, 1))
    with button_cols[0]:
        pass

    st.markdown("**SAP Agents configuration**")
    agent_cols = st.columns(2)
    with agent_cols[0]:
        st.text_input("Agent name", key="sap_agent_name")
        st.text_area("Expert in", key="sap_agent_expert_in", height=110)
    with agent_cols[1]:
        st.text_area("Initial instructions", key="sap_agent_instructions", height=160)
        st.caption(
            "Agent type fixed to 'smart', safety checks enabled, iterations set to 100, models: OpenAiGpt4oMini → OpenAiGpt4o."
        )

    payload_ready = True

    with button_cols[1]:
        generate_clicked = st.button(
            "🚀 Generate agent",
            type="primary",
            disabled=not payload_ready,
            use_container_width=True,
        )

    if generate_clicked:
        debug_lines: List[str] = []
        hana_success = False
        conn = None
        schema_name = sanitize_identifier(
            payload.get("schemaName", f"{st.session_state.get('customer', 'agent')}_schema"),
            fallback="JOULE_SCHEMA",
        )
        payload["schemaName"] = schema_name

        # HANA provisioning with detailed debug info (optional)
        if os.getenv("JOULE_SKIP_HANA", "true").lower() == "true":
            debug_lines.append("Skipping HANA provisioning (JOULE_SKIP_HANA=true).")
        else:
            try:
                conn = hana_connect()
                debug_lines.append(
                    f"Connected to HANA at {os.getenv('HANA_HOST','?')}:{os.getenv('HANA_PORT','443')} as {os.getenv('HANA_USER','?')}"
                )
                ensure_catalog(conn)
                debug_lines.append(f"Ensured catalog schema '{os.getenv('HANA_CATALOG_SCHEMA', 'AGENT_CATALOG')}'")

                table_models = [TableDefinition(**table) for table in payload.get("tables", [])]
                with st.spinner("Provisioning HANA schema and loading tables…"):
                    create_schema_with_tables(conn, schema_name, table_models)
                    debug_lines.append(f"Created/updated schema '{schema_name}' with {len(table_models)} tables")

                    # Inspect row counts for created tables
                    try:
                        cur = conn.cursor()
                        for t in table_models:
                            tname = sanitize_identifier(t.name)
                            cur.execute(f'SELECT COUNT(*) FROM "{schema_name}"."{tname}"')
                            count = cur.fetchone()[0]
                            debug_lines.append(f"Table {schema_name}.{tname}: {count} rows")
                    except Exception as count_exc:
                        debug_lines.append(f"Row count check failed: {count_exc}")

                    register_agent_metadata(
                        conn,
                        agent_id=str(uuid.uuid4()),
                        agent_name=payload.get("name", "SAP Joule Agent"),
                        use_case=payload.get("UseCase", payload.get("useCase", "")),
                        customer=payload.get("customer", ""),
                        schema_name=schema_name,
                        prompt=payload.get("prompt", ""),
                        business_case_card=payload.get("businessCaseCard", ""),
                        tables=table_models,
                    )
                    debug_lines.append("Registered agent metadata in catalog")
                    hana_success = True
                    st.success(f"HANA schema '{schema_name}' created and tables populated.")
            except Exception as exc:  # pragma: no cover - HANA diagnostics
                st.session_state["agent_error"] = f"HANA provisioning failed: {exc}"
                st.error(st.session_state["agent_error"])
                debug_lines.append("HANA error:\n" + traceback.format_exc())
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:  # pragma: no cover - cleanup best effort
                        pass

        # SAP Agent creation and tool attachment with debug info
        try:
            from create_agent import create_agent

            with st.spinner("Creating SAP Agent via SAP Agents service…"):
                data = create_agent(
                    payload={
                        "name": st.session_state.get("sap_agent_name", "Web Search Expert").strip()
                        or "Web Search Expert",
                        "type": "smart",
                        "safetyCheck": True,
                        "expertIn": st.session_state.get("sap_agent_expert_in", "").strip()
                        or "You are an expert in searching the web",
                        "initialInstructions": st.session_state.get("sap_agent_instructions", "").strip()
                        or "## WebSearch Tool Hint\nTry to append 'Wikipedia' to your search query",
                        "iterations": 100,
                        "baseModel": "OpenAiGpt4oMini",
                        "advancedModel": "OpenAiGpt4o",
                    }
                )

            agent_id = data.get("id") or data.get("agentId")
            if not agent_id:
                st.session_state["agent_error"] = "SAP Agents response did not include an agent identifier."
                st.error(st.session_state["agent_error"])
                return
            else:
                debug_lines.append(f"Created SAP Agent with id {agent_id}")
            debug_lines.append(f"SAP Agents base URL: {os.getenv('SAP_AGENT_BASE_URL','(unset)')}")

            with st.spinner("Provisioning default SAP Joule tools…"):
                tool_summaries = provision_agent_tools(agent_id)

            st.session_state["agent_success"] = data
            st.session_state["agent_tools"] = tool_summaries
            st.session_state["agent_error"] = None

            st.success("Agent created and default tools provisioned in SAP Agents.")
            st.json(data)
            if tool_summaries:
                st.markdown("**Attached tools**")
                st.write(
                    ", ".join(
                        f"{tool['name']} ({tool['type']})".strip() for tool in tool_summaries if tool.get("name")
                    )
                )
                # Surface raw tool API responses under debug
                try:
                    st.markdown("Tool attachment responses (raw)")
                    st.json(tool_summaries)
                except Exception:
                    pass

            debug_lines.append(
                "Tools attached: " + ", ".join(
                    f"{t.get('name')} ({t.get('type')})" for t in tool_summaries if t.get('name')
                )
            )
        except ImportError as exc:
            st.session_state["agent_error"] = f"Unable to import create_agent helper: {exc}"
            st.session_state["agent_tools"] = []
            st.error(st.session_state["agent_error"])
            debug_lines.append("Import error:\n" + traceback.format_exc())
        except SAPAgentAPIError as exc:
            if getattr(exc, "status_code", None) == 409:
                # Conflict: agent name already exists. Retry creation with a unique name and attach tools to the new agent.
                try:
                    from create_agent import create_agent as _create_agent_retry
                    base_name = st.session_state.get("sap_agent_name", "Web Search Expert").strip() or "Web Search Expert"
                    unique_suffix = str(uuid.uuid4())[:8]
                    new_name = f"{base_name}-{unique_suffix}"
                    debug_lines.append(f"409 conflict. Retrying with unique name '{new_name}'")
                    with st.spinner("Retrying agent creation with a unique name…"):
                        data = _create_agent_retry(
                            payload={
                                "name": new_name,
                                "type": "smart",
                                "safetyCheck": True,
                                "expertIn": st.session_state.get("sap_agent_expert_in", "").strip()
                                or "You are an expert in searching the web",
                                "initialInstructions": st.session_state.get("sap_agent_instructions", "").strip()
                                or "## WebSearch Tool Hint\nTry to append 'Wikipedia' to your search query",
                                "iterations": 100,
                                "baseModel": "OpenAiGpt4oMini",
                                "advancedModel": "OpenAiGpt4o",
                            }
                        )
                    agent_id = data.get("id") or data.get("agentId") or data.get("ID") or data.get("Id")
                    if not agent_id:
                        st.session_state["agent_error"] = "SAP Agents response did not include an agent identifier after retry."
                        st.error(st.session_state["agent_error"])
                        return

                    with st.spinner("Provisioning default SAP Joule tools…"):
                        tool_summaries = provision_agent_tools(agent_id)

                    st.session_state["agent_success"] = data
                    st.session_state["agent_tools"] = tool_summaries
                    st.session_state["agent_error"] = None
                    st.success("Agent created with a unique name and tools attached.")
                except Exception as rex:
                    st.session_state["agent_error"] = f"Agent creation retry failed: {rex}"
                    st.session_state["agent_tools"] = []
                    st.error(st.session_state["agent_error"])
                    debug_lines.append(f"Retry after 409 failed: {rex}")
            else:
                st.session_state["agent_error"] = "SAP Agents API error"
                st.session_state["agent_tools"] = []
                debug_lines.append(f"SAP Agents API error ({getattr(exc,'status_code',None)}): {exc}")
        except Exception as exc:  # pragma: no cover
            st.session_state["agent_error"] = f"Agent creation workflow failed: {exc}"
            st.session_state["agent_tools"] = []
            st.error(st.session_state["agent_error"])
            debug_lines.append("Agent creation error:\n" + traceback.format_exc())

        # Debug details suppressed per requirements



    with st.expander("Agent payload (JSON)", expanded=False):
        st.code(json.dumps(payload, indent=2), language="json")

    if st.session_state.get("agent_success") and st.session_state.get("agent_tools"):
        st.link_button("Open SAP Agents workspace →", SAP_AGENT_UI_URL)
    elif st.session_state.get("agent_success") and not st.session_state.get("agent_error"):
        st.info("Agent created, but no tools were attached. Attach tools before visiting the workspace.")


if __name__ == "__main__":
    streamlit_app()
