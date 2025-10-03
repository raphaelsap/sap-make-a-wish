"""Streamlit app for generating SAP Joule agents via Perplexity."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import requests
import streamlit as st

from sap_agents_api import SAPAgentAPIError, get_default_client


PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_PPLX_MODEL = os.getenv("PPLX_MODEL", "sonar")


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
    except json.JSONDecodeError as exc:
        raise ValueError("Perplexity response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Perplexity response must be a JSON object")

    tables = parsed.get("tables")
    if not isinstance(tables, list) or not tables:
        raise ValueError("Perplexity response missing tables array")

    return parsed


def build_messages(customer: str, use_case: str) -> List[Dict[str, str]]:
    instruction = (
        "You are SAP Joule, an SAP BTP solution advisor. Respond with compact JSON only, matching "
        "{\"agentName\",\"agentPrompt\",\"schemaName\",\"businessCaseCard\",\"tables\"}. "
        "Each table must include name, desc, columns (name,type,description,nullable,isPrimaryKey), and sample rows. "
        "Deliver SAP-aligned terminology, ensure schemaName is uppercase with underscores derived from customer and use case, "
        "and conclude agentPrompt with 'Joule Tip: <insight>'."
    )
    scenario = (
        f"Customer: {customer}\n"
        f"Use case: {use_case}\n"
        "Return at least 6 SAP-relevant tables covering data sources, KPIs, and enablement assets for this scenario. "
        "Provide a compelling agentName and a businessCaseCard string with emoji headers (Problem, Solution, Benefits, ROI)."
    )
    return [
        {"role": "system", "content": instruction},
        {"role": "user", "content": scenario},
    ]


def request_demo_package(customer: str, use_case: str) -> Dict[str, Any]:
    api_key = os.getenv("PPLX_API_KEY")
    if not api_key:
        raise RuntimeError("Set PPLX_API_KEY in your environment to call Perplexity.")

    payload = {
        "model": DEFAULT_PPLX_MODEL,
        "messages": build_messages(customer, use_case),
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
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Unexpected Perplexity response shape") from exc

    parsed = parse_llm_payload(content)
    return parsed


def build_agent_payload(package: Dict[str, Any], customer: str, use_case: str) -> Dict[str, Any]:
    return {
        "name": package.get("agentName", "SAP Joule Agent"),
        "prompt": package.get("agentPrompt", "").strip(),
        "customer": customer.strip(),
        "useCase": use_case.strip(),
        "schemaName": package.get("schemaName", "JOULE_DEMO_SCHEMA"),
        "tables": package.get("tables", []),
        "businessCaseCard": package.get("businessCaseCard", ""),
    }


def display_tables(tables: List[Dict[str, Any]]) -> None:
    st.markdown("**Tables prepared by SAP Joule**")
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


def streamlit_app() -> None:
    st.set_page_config(page_title="SAP BTP - Make a Wish", layout="wide")
    st.title("SAP BTP Agents - Make a Wish 🪄")
    st.caption("Describe the customer scenario, let Perplexity + SAP Joule craft the agent, then create it in SAP Agents.")

    with st.form("scenario-form"):
        customer = st.text_input("Customer name", value=st.session_state.get("customer", ""))
        use_case = st.text_area(
            "Use case",
            value=st.session_state.get("use_case", ""),
            placeholder="Describe the outcome, scope, and SAP capabilities to highlight.",
        )
        submitted = st.form_submit_button("Generate with Perplexity")

    if submitted:
        if not customer.strip() or not use_case.strip():
            st.error("Please provide both a customer name and use case before generating.")
        else:
            with st.spinner("Calling Perplexity to assemble the SAP Joule proposal…"):
                try:
                    package = request_demo_package(customer, use_case)
                except Exception as exc:  # pragma: no cover - surfaced to UI
                    st.session_state.pop("demo_package", None)
                    st.error(f"Unable to generate the proposal: {exc}")
                else:
                    st.session_state["demo_package"] = package
                    st.session_state["customer"] = customer.strip()
                    st.session_state["use_case"] = use_case.strip()
                    st.session_state.pop("agent_success", None)
                    st.session_state.pop("agent_error", None)
                    st.success("Perplexity response received. Review the proposal below.")

    package = st.session_state.get("demo_package")
    if not package:
        st.info("Enter scenario details above and click Generate to see the SAP Joule proposal.")
        return

    st.divider()
    st.subheader("SAP Joule proposal")

    info_cols = st.columns(2)
    info_cols[0].metric("Agent name", package.get("agentName", "—"))
    info_cols[1].metric("Schema name", package.get("schemaName", "—"))

    st.markdown("**Agent prompt**")
    st.code(package.get("agentPrompt", ""), language="text")

    st.markdown("**Business case card**")
    st.code(package.get("businessCaseCard", ""), language="text")

    tables = package.get("tables", [])
    if tables:
        display_tables(tables)
    else:
        st.warning("Perplexity did not return any tables for this scenario.")

    st.divider()
    st.subheader("Create the SAP agent")

    payload = build_agent_payload(
        package,
        st.session_state.get("customer", ""),
        st.session_state.get("use_case", ""),
    )
    payload_ready = all(
        [
            payload.get("name"),
            payload.get("prompt"),
            payload.get("customer"),
            payload.get("useCase"),
            payload.get("tables"),
        ]
    )

    if st.button("Generate agent", type="primary", disabled=not payload_ready):
        try:
            client = get_default_client()
            response = client.create_agent(payload)
        except RuntimeError as exc:
            st.session_state["agent_error"] = f"SAP agent configuration missing: {exc}"
            st.error(st.session_state["agent_error"])
        except SAPAgentAPIError as exc:
            st.session_state["agent_error"] = f"SAP Agents API error ({exc.status_code}): {exc}"
            st.error(st.session_state["agent_error"])
        except Exception as exc:  # pragma: no cover
            st.session_state["agent_error"] = f"Unexpected error creating agent: {exc}"
            st.error(st.session_state["agent_error"])
        else:
            st.session_state["agent_success"] = response
            st.session_state["agent_error"] = None
            st.success("Agent created successfully via SAP Agents API.")
            st.json(response)

    if st.session_state.get("agent_error"):
        st.warning(st.session_state["agent_error"])

    with st.expander("Agent payload (JSON)", expanded=False):
        st.code(json.dumps(payload, indent=2), language="json")


if __name__ == "__main__":
    streamlit_app()
