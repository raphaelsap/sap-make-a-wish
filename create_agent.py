"""Utility script for creating a simple SAP AI agent via the SAP Agents API."""
from __future__ import annotations
import logging
from typing import Any, Dict
from dotenv import load_dotenv
from sap_agents_api import SAPAgentAPIError, SAPAgentsClient, get_default_client

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _ensure_env_loaded() -> None:
    """Load environment variables from a local .env file, if present."""
    load_dotenv()


def build_basic_payload(name: str = "Web Search Expert") -> Dict[str, Any]:
    """Return a minimal payload compatible with the SAP Agents create endpoint."""
    return {
        "name": name,
        "type": "smart",
        "safetyCheck": True,
        "expertIn": "You are an expert in searching the web",
        "initialInstructions": "## WebSearch Tool Hint\nTry to append 'Wikipedia' to your search query",
        "iterations": 20,
        "baseModel": "OpenAiGpt4oMini",
        "advancedModel": "OpenAiGpt4o",
    }


def create_agent(client: SAPAgentsClient | None = None, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Create an SAP agent using the provided payload.

    Parameters
    ----------
    client:
        Optional pre-configured :class:`SAPAgentsClient`. When omitted, the default
        client is constructed from environment variables (``SAP_AGENT_*``).
    payload:
        Custom payload to send to the API. If ``None``, :func:`build_basic_payload`
        supplies the default body.
    """
    _ensure_env_loaded()
    client = client or get_default_client()
    token = client._get_token()  # pylint: disable=protected-access
    #LOGGER.info("Obtained OAuth token: %s", token)
    payload = payload or build_basic_payload()
    LOGGER.info("Creating agent '%s' via SAP Agents API", payload.get("name"))
    return client.create_agent(payload)


def main() -> None:
    _ensure_env_loaded()
    try:
        response = create_agent()
    except SAPAgentAPIError as exc:
        LOGGER.error("SAP Agent creation failed (status %s): %s", exc.status_code, exc)
    except Exception as exc:  # pragma: no cover - top level diagnostic
        LOGGER.exception("Unexpected error while creating agent: %s", exc)
    else:
        LOGGER.info("Agent created successfully: %s", response)


if __name__ == "__main__":
    main()
