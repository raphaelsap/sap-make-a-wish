"""Create a SAP Agent and attach tools from a JSON file.

Usage:
  python3 create_from_json.py samples/agent_package.json [-o output.json]

JSON structure:
{
  "agent": { ... SAP Agents create payload ... },
  "tools": [
    { "name": "...", "type": "...", "config": [ { "name": "...", "value": "..." }, ... ] }
  ]
}

Environment:
- Loads environment variables from .env (python-dotenv).
- Requires SAP_AGENT_BASE_URL, SAP_AGENT_OAUTH_URL, SAP_AGENT_CLIENT_ID, SAP_AGENT_CLIENT_SECRET.
- Optionally SAP_AGENT_UI_BASE_URL to print a link to the created agent.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from sap_agents_api import SAPAgentAPIError, create_agent_tool, get_default_client

LOGGER = logging.getLogger("create_from_json")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _ensure_env() -> None:
    """Load environment variables from a local .env file, if present."""
    load_dotenv()


def _extract_agent_id(resp: Dict[str, Any]) -> Optional[str]:
    """Try to extract an agent identifier from various possible response shapes."""
    if not isinstance(resp, dict):
        return None

    # Common top-level keys
    for key in ("id", "agentId", "ID", "Id"):
        val = resp.get(key)
        if val:
            return str(val)

    # Some flows may wrap the SAP Agents response
    nested = resp.get("sapAgentResponse") or resp.get("data")
    if isinstance(nested, dict):
        for key in ("id", "agentId", "ID", "Id"):
            val = nested.get(key)
            if val:
                return str(val)

    return None


def _normalize_tool_payload(tool: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure tool payload has proper structure: name, type, config list of {name, value}."""
    name = str(tool.get("name", "Unnamed Tool"))
    tool_type = str(tool.get("type", "")).strip()
    cfg_list = tool.get("config") or []
    if not isinstance(cfg_list, list):
        raise ValueError("tool.config must be a list of {name, value} entries")

    normalized_config: List[Dict[str, Any]] = []
    for entry in cfg_list:
        if not isinstance(entry, dict):
            raise ValueError("tool.config entries must be objects with name/value")
        n = str(entry.get("name", "")).strip()
        if not n:
            raise ValueError("tool.config entry missing name")
        # Keep value type as-is; API may accept strings, numbers, or booleans
        v = entry.get("value", "")
        normalized_config.append({"name": n, "value": v})

    return {"name": name, "type": tool_type, "config": normalized_config}


def create_agent_and_attach_tools(json_path: str) -> Dict[str, Any]:
    """Create agent from JSON and attach tools. Returns a summary dict."""
    _ensure_env()
    try:
        client = get_default_client()
    except RuntimeError as exc:
        raise RuntimeError(f"SAP Agents configuration missing: {exc}") from exc

    # Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    agent_payload = data.get("agent")
    tools = data.get("tools", [])

    if not isinstance(agent_payload, dict):
        raise ValueError("JSON must include an 'agent' object")
    if tools and not isinstance(tools, list):
        raise ValueError("'tools' must be an array")

    LOGGER.info("Creating agent '%s'...", agent_payload.get("name", "SAP Agent"))
    try:
        agent_resp = client.create_agent(agent_payload)
    except SAPAgentAPIError as exc:
        raise RuntimeError(f"SAP Agent creation failed ({exc.status_code}): {exc}") from exc

    agent_id = _extract_agent_id(agent_resp)
    if not agent_id:
        LOGGER.error("Agent creation response did not include an identifier: %s", json.dumps(agent_resp, indent=2))
        raise RuntimeError("SAP Agents response did not include an agent identifier")

    LOGGER.info("Agent created with ID: %s", agent_id)

    attached: List[Dict[str, Any]] = []
    for tool in tools:
        payload = _normalize_tool_payload(tool)
        if not payload.get("type"):
            LOGGER.warning("Skipping tool without type: %s", payload)
            continue
        LOGGER.info("Attaching tool '%s' (%s)...", payload.get("name", ""), payload.get("type", ""))
        try:
            res = create_agent_tool(agent_id, payload)
        except SAPAgentAPIError as exc:
            LOGGER.error("Failed to attach tool '%s' (%s): %s", payload.get("name", ""), payload.get("type", ""), exc)
            raise
        attached.append({"request": payload, "response": res})

    ui_base = os.getenv("SAP_AGENT_UI_BASE_URL")
    agent_url = f"{ui_base.rstrip('/')}/{agent_id}" if ui_base and agent_id else None

    summary: Dict[str, Any] = {
        "agentId": agent_id,
        "agentUrl": agent_url,
        "agentResponse": agent_resp,
        "attachedTools": attached,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Create SAP Agent and attach tools from a JSON file.")
    parser.add_argument("json_path", help="Path to JSON file, e.g., samples/agent_package.json")
    parser.add_argument("-o", "--output", help="Path to write a result JSON summary (optional)")
    args = parser.parse_args()

    try:
        summary = create_agent_and_attach_tools(args.json_path)
    except Exception as exc:
        LOGGER.error("Operation failed: %s", exc)
        sys.exit(1)
    else:
        print(json.dumps(summary, indent=2))
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2)
                LOGGER.info("Wrote summary to %s", args.output)
            except Exception as write_exc:
                LOGGER.error("Failed to write output file: %s", write_exc)


if __name__ == "__main__":
    main()
