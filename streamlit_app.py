"""Streamlit app for generating SAP Joule agents via Perplexity."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

from markdown import markdown
from fpdf import FPDF


PPLX_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_PPLX_MODEL = os.getenv("PPLX_MODEL", "sonar")
PROMPT_FILE = Path(__file__).parent / "prompts" / "perplexity.md"
SAP_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/5/59/SAP_2011_logo.svg"
BACKEND_AGENT_ENDPOINT = os.getenv("BACKEND_AGENT_ENDPOINT", "http://localhost:8000/api/agents")


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
        "Return at least 6 SAP-relevant tables covering data sources, KPIs, and enablement assets for this scenario. "
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
                color: #e2e8f0;
                text-shadow: 0 0 14px rgba(59,130,246,0.35);
            }}
        </style>
        <div class="holo-card"><div class="holo-content">{html_content}</div></div>
        """,
        unsafe_allow_html=True,
    )


def generate_pdf_from_markdown(markdown_text: str) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def set_body_font() -> None:
        pdf.set_font("Helvetica", size=11)

    set_body_font()
    is_code_block = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            is_code_block = not is_code_block
            if is_code_block:
                pdf.set_font("Courier", size=9)
            else:
                set_body_font()
            continue

        if is_code_block:
            pdf.multi_cell(0, 5, line or " ")
            continue

        stripped = line.strip()
        if not stripped:
            pdf.ln(4)
            continue

        if stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, stripped[4:])
            pdf.ln(2)
            set_body_font()
        elif stripped.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 8, stripped[3:])
            pdf.ln(2)
            set_body_font()
        elif stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 9, stripped[2:])
            pdf.ln(3)
            set_body_font()
        elif stripped.startswith("- "):
            set_body_font()
            pdf.multi_cell(0, 6, f"• {stripped[2:]}")
        elif stripped.startswith("| ") and stripped.endswith("|"):
            set_body_font()
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            pdf.multi_cell(0, 6, " | ".join(cells))
        else:
            set_body_font()
            pdf.multi_cell(0, 6, stripped)

    return pdf.output(dest="S").encode("latin-1")


def build_summary_markdown(package: Dict[str, Any]) -> str:
    customer = st.session_state.get("customer", "—")
    use_case = st.session_state.get("use_case", "—")
    main_solution = st.session_state.get("main_solution", "—")
    metric = st.session_state.get("metric", "—")
    agent_name = st.session_state.get("agent_name_edit", package.get("agentName", "—"))
    schema_name = st.session_state.get("schema_name_edit", package.get("schemaName", "—"))
    agent_prompt = st.session_state.get("agent_prompt_edit", package.get("agentPrompt", ""))
    business_case = st.session_state.get("business_case_card_edit", package.get("businessCaseCard", ""))

    lines: List[str] = [
        "# SAP BTP - Make a Wish Summary",
        "",
        "## Scenario Overview",
        f"- **Customer:** {customer}",
        f"- **Use case:** {use_case}",
        f"- **Main SAP solution:** {main_solution}",
        f"- **Optimisation metric:** {metric}",
        "",
        "## Agent Configuration",
        f"- **Agent name:** {agent_name}",
        f"- **Schema name:** {schema_name}",
        "",
        "### Agent Prompt",
        "```",
        agent_prompt.strip(),
        "```",
        "",
        "### Business Case Card",
        business_case.strip() or "_(No business case provided.)_",
        "",
        "## Tables",
    ]

    tables = package.get("tables", [])
    if not tables:
        lines.append("_(No tables returned by Perplexity.)_")
    else:
        for table in tables:
            table_name = table.get("name", "Unnamed table")
            desc = table.get("desc", "")
            lines.extend(
                [
                    f"### Table: {table_name}",
                    desc if desc else "",
                    "",
                    "| Column | Type | Nullable | Primary | Description |",
                    "| --- | --- | --- | --- | --- |",
                ]
            )
            for column in table.get("columns", []):
                lines.append(
                    f"| {column.get('name', '')} | {column.get('type', '')} | "
                    f"{'Yes' if column.get('nullable', True) else 'No'} | "
                    f"{'Yes' if column.get('isPrimaryKey') else 'No'} | {column.get('description', '')} |"
                )

            rows = table.get("rows", [])
            if rows:
                lines.extend([
                    "",
                    "Sample rows:",
                    "```json",
                    json.dumps(rows[:3], indent=2),
                    "```",
                ])
            lines.append("")

    return "\n".join(lines).strip()


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

    header_cols = st.columns([1, 3])
    with header_cols[0]:
        st.image(SAP_LOGO_URL, width=120)
    with header_cols[1]:
        st.title("Joule x BTP - Make a Wish ✨")
        st.caption(
            "Describe the customer scenario, highlight the SAP solution and metric, then let Perplexity + SAP Joule craft the agent."
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
        submitted = st.form_submit_button("Generate with Perplexity  🚀")

    if submitted:
        if not customer.strip() or not use_case.strip():
            st.error("Please provide both a customer name and use case before generating.")
        else:
            with st.spinner("Calling Perplexity to assemble the SAP Joule proposal…"):
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
                    st.session_state.pop("agent_success", None)
                    st.session_state.pop("agent_error", None)
                    st.success("Perplexity response received. Review the proposal below.")

    package = st.session_state.get("demo_package")
    if not package:
        st.info("Enter scenario details above and click Generate to see the SAP Joule proposal.")
        return

    st.divider()
    st.subheader("SAP Joule proposal 🪄")

    info_cols = st.columns(4)
    info_cols[0].metric("Agent name", st.session_state.get("agent_name_edit", package.get("agentName", "—")))
    info_cols[1].metric("Schema name", st.session_state.get("schema_name_edit", package.get("schemaName", "—")))
    info_cols[2].metric("Main SAP solution", st.session_state.get("main_solution", "—"))
    info_cols[3].metric("Optimisation metric", st.session_state.get("metric", "—"))

    st.markdown("**🛠 Editable details**")
    edit_cols = st.columns(2)
    with edit_cols[0]:
        st.text_input("Agent name", key="agent_name_edit")
        st.text_input("Schema name", key="schema_name_edit")
    with edit_cols[1]:
        st.text_area("Agent prompt", key="agent_prompt_edit", height=220)

    st.markdown("**🎴 Business case card (editable & preview)**")
    st.text_area("Business case narrative", key="business_case_card_edit", height=220)
    render_holographic_card(st.session_state.get("business_case_card_edit", ""))

    st.markdown("**🧠 Agent prompt preview**")
    st.code(st.session_state.get("agent_prompt_edit", ""), language="text")

    tables = package.get("tables", [])
    if tables:
        display_tables(tables)
    else:
        st.warning("Perplexity did not return any tables for this scenario.")

    st.divider()
    st.subheader("Iterate on the proposal 🔁")
    st.markdown("Provide additional instructions for Perplexity to refine the agent.")
    st.text_area(
        "Adjustments or change requests",
        key="refinement_text",
        placeholder="e.g. Emphasise SAP Datasphere KPIs and add a sustainability table.",
        height=140,
    )

    if st.button("✨ Regenerate with adjustments", type="secondary"):
        refinement_text = st.session_state.get("refinement_text", "")
        if not refinement_text.strip():
            st.warning("Enter some refinement instructions before regenerating.")
        else:
            with st.spinner("Revising proposal with Perplexity…"):
                regenerate_proposal(refinement_text)

    st.divider()
    st.subheader("Create the SAP agent ✅")

    payload = build_agent_payload(
        package,
        st.session_state.get("customer", ""),
        st.session_state.get("use_case", ""),
    )
    summary_markdown = build_summary_markdown(package)
    pdf_bytes = generate_pdf_from_markdown(summary_markdown)

    st.download_button(
        "Generate PDF summary 📑",
        data=pdf_bytes,
        file_name=f"sap-btp-make-a-wish-{st.session_state.get('schema_name_edit', 'agent')}.pdf",
        mime="application/pdf",
        use_container_width=True,
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

    if st.button("🚀 Generate agent", type="primary", disabled=not payload_ready):
        if not BACKEND_AGENT_ENDPOINT:
            st.session_state["agent_error"] = "BACKEND_AGENT_ENDPOINT is not configured."
            st.error(st.session_state["agent_error"])
        else:
            try:
                with st.spinner("Deploying schema, loading tables, and creating SAP agent…"):
                    response = requests.post(
                        BACKEND_AGENT_ENDPOINT,
                        json=payload,
                        timeout=180,
                    )
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                st.session_state["agent_error"] = f"Backend request failed: {exc}"
                st.error(st.session_state["agent_error"])
            except ValueError as exc:  # JSON decode issues
                st.session_state["agent_error"] = f"Backend returned invalid JSON: {exc}"
                st.error(st.session_state["agent_error"])
            else:
                st.session_state["agent_success"] = data
                st.session_state["agent_error"] = None
                st.success("Agent created successfully. HANA schema provisioned and SAP Agents entry ready.")
                st.json(data)

    if st.session_state.get("agent_error"):
        st.warning(st.session_state["agent_error"])

    with st.expander("Agent payload (JSON)", expanded=False):
        st.code(json.dumps(payload, indent=2), language="json")


if __name__ == "__main__":
    streamlit_app()
