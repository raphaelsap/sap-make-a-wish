"""Create an SAP Agent and attach a single Perplexity tool.

Usage:
  source .venv/bin/activate && python attach_perplexity_tool.py [--name "Agent Name"] [--agent-id EXISTING_ID]

Behavior:
- If --agent-id is provided, attaches the Perplexity tool to that agent.
- Otherwise, creates a new agent (defaults to "Perplexity Tool Demo Agent", configurable via --name),
  then attaches the Perplexity tool.
- Tries config name "perplexity" first; if the landscape rejects it, retries with "destination".
- If the create-agent response doesn't include an id, it falls back to listing agents to resolve it.

Environment:
- Loads .env with python-dotenv.
- Requires SAP_AGENT_BASE_URL, SAP_AGENT_OAUTH_URL, SAP_AGENT_CLIENT_ID, SAP_AGENT_CLIENT_SECRET.
- Optional PPLX_DESTINATION to override the tool value (default "perplexity").
- Prints a summary JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from sap_agents_api import (
    SAPAgentAPIError,
    SAPAgentsClient,
    get_default_client,
    list_agents as list_agents_api,
)


def build_default_agent_payload(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "smart",
        "safetyCheck": True,
        "expertIn": "You are an expert in searching the web",
        "initialInstructions": "## WebSearch Tool Hint\nTry to append 'Wikipedia' to your search query",
        "iterations": 100,
        "baseModel": "OpenAiGpt4oMini",
        "advancedModel": "OpenAiGpt4o",
    }


def extract_agent_id(resp: Any) -> Optional[str]:
    if isinstance(resp, dict):
        for key in ("id", "agentId", "ID", "Id"):
            if resp.get(key):
                return str(resp.get(key))
        nested = resp.get("sapAgentResponse") or resp.get("data")
        if isinstance(nested, dict):
            for key in ("id", "agentId", "ID", "Id"):
                if nested.get(key):
                    return str(nested.get(key))
    return None


def resolve_agent_id_by_listing(target_name: Optional[str] = None) -> Optional[str]:
    try:
        agents = list_agents_api()
    except Exception:
        return None

    items: List[Dict[str, Any]] = []
    if isinstance(agents, dict):
        if isinstance(agents.get("value"), list):
            items = agents["value"]
        elif isinstance(agents.get("items"), list):
            items = agents["items"]
    elif isinstance(agents, list):
        items = agents

    # Try exact name match first
    if target_name:
        for it in items:
            name = (it.get("name") or it.get("Name") or "").strip()
            _id = it.get("id") or it.get("agentId") or it.get("ID") or it.get("Id")
            if name == target_name and _id:
                return str(_id)

    # Fallback to last item with an id
    for it in reversed(items):
        _id = it.get("id") or it.get("agentId") or it.get("ID") or it.get("Id")
        if _id:
            return str(_id)

    return None


def attach_perplexity_tool(client: SAPAgentsClient, agent_id: str) -> Dict[str, Any]:
    dest_value = os.getenv("PPLX_DESTINATION", "perplexity").strip() or "perplexity"

    primary_payload = {
        "name": "Perplexity Destination",
        "type": "bringyourown",
        "config": [{"name": "destination", "value": dest_value}],
    }

    try:
        res = client.create_tool(agent_id, primary_payload)
        return {
            "request": primary_payload,
            "response": res,
            "status": "ok",
        }
    except SAPAgentAPIError as exc:
        # Fallback to alternate schema using 'perplexity'
        alt_payload = {
            "name": "Web Search Tool",
            "type": "bringyourown",
            "config": [{"name": "perplexity", "value": dest_value}],
        }
        try:
            alt_res = client.create_tool(agent_id, alt_payload)
            return {
                "request": alt_payload,
                "response": alt_res,
                "status": "ok_fallback",
                "fallbackFrom": primary_payload["name"],
                "primaryError": str(exc),
                "primaryStatus": getattr(exc, "status_code", None),
            }
        except SAPAgentAPIError as exc2:
            return {
                "request": alt_payload,
                "response": {"error": str(exc2), "status": getattr(exc2, "status_code", None)},
                "status": "error",
                "fallbackFrom": primary_payload["name"],
                "primaryError": str(exc),
                "primaryStatus": getattr(exc, "status_code", None),
            }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create agent and attach a single Perplexity tool.")
    parser.add_argument("--name", default="Perplexity Tool Demo Agent", help="Agent name (for creation)")
    parser.add_argument("--agent-id", help="Attach tool to an existing agent id instead of creating a new one")
    args = parser.parse_args()

    summary: Dict[str, Any] = {
        "agentId": None,
        "agentCreateResponse": None,
        "toolAttachment": None,
        "uiLink": None,
    }

    try:
        client = get_default_client()
    except Exception as e:
        print(json.dumps({"error": f"SAP Agents client init failed: {e}"}))
        sys.exit(1)

    agent_id = args.agent_id

    if not agent_id:
        # Create new agent
        payload = build_default_agent_payload(args.name)
        try:
            create_resp = client.create_agent(payload)
            summary["agentCreateResponse"] = create_resp
        except SAPAgentAPIError as exc:
            print(json.dumps({"error": f"Agent creation failed ({exc.status_code}): {exc}"}))
            sys.exit(1)

        agent_id = extract_agent_id(summary["agentCreateResponse"])
        if not agent_id:
            # Fallback to listing
            agent_id = resolve_agent_id_by_listing(target_name=args.name)

        if not agent_id:
            print(json.dumps({"error": "Could not resolve agentId after creation"}))
            sys.exit(1)

    summary["agentId"] = agent_id

    # Attach the single Perplexity tool
    tool_result = attach_perplexity_tool(client, agent_id)
    summary["toolAttachment"] = tool_result

    # Compose UI link if base provided
    ui_base = os.getenv("SAP_AGENT_UI_BASE_URL", "").strip()
    if ui_base:
        summary["uiLink"] = ui_base.rstrip("/") + "/" + agent_id

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
