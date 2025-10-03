"""Lightweight client for the SAP Agents service."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests


class SAPAgentAPIError(RuntimeError):
    """Raised when the SAP Agents service returns an error."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, payload: Optional[Any] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass
class OAuthToken:
    value: str
    expires_at: float

    @property
    def is_valid(self) -> bool:
        # Refresh slightly early to prevent race conditions.
        return time.time() < (self.expires_at - 60)


class SAPAgentsClient:
    """Wrapper around the SAP Agents REST API."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        oauth_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv('SAP_AGENT_BASE_URL', '')).rstrip('/') + '/'
        self.oauth_url = oauth_url or os.getenv('SAP_AGENT_OAUTH_URL')
        self.client_id = client_id or os.getenv('SAP_AGENT_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('SAP_AGENT_CLIENT_SECRET')
        self.session = session or requests.Session()
        self._token: Optional[OAuthToken] = None

        if not all([self.base_url.strip(), self.oauth_url, self.client_id, self.client_secret]):
            raise RuntimeError(
                'Missing SAP agent configuration. Set SAP_AGENT_BASE_URL, SAP_AGENT_OAUTH_URL, '
                'SAP_AGENT_CLIENT_ID, and SAP_AGENT_CLIENT_SECRET in the environment.'
            )

    def _obtain_token(self) -> OAuthToken:
        response = self.session.post(
            self.oauth_url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise SAPAgentAPIError('Failed to obtain OAuth token', status_code=response.status_code, payload=response.text)

        data: Dict[str, Any] = response.json()
        token = data.get('access_token')
        expires_in = data.get('expires_in', 0)

        if not token:
            raise SAPAgentAPIError('OAuth token missing in response', payload=data)

        return OAuthToken(value=token, expires_at=time.time() + float(expires_in or 0))

    def _get_token(self) -> str:
        if self._token is None or not self._token.is_valid:
            self._token = self._obtain_token()
        return self._token.value

    def _build_url(self, path: str) -> str:
        if path.startswith('http://') or path.startswith('https://'):
            return path
        return urljoin(self.base_url, path.lstrip('/'))

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        token = self._get_token()
        response = self.session.post(
            self._build_url(path),
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json=payload or {},
            timeout=60,
        )

        if response.status_code >= 400:
            raise SAPAgentAPIError(
                f'SAP Agents POST {path} failed with status {response.status_code}',
                status_code=response.status_code,
                payload=response.text,
            )

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - surface upstream
            raise SAPAgentAPIError('SAP Agents response was not valid JSON', payload=response.text) from exc

    def create_agent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.post('Agents', payload)


_default_client: Optional[SAPAgentsClient] = None


def get_default_client() -> SAPAgentsClient:
    global _default_client
    if _default_client is None:
        _default_client = SAPAgentsClient()
    return _default_client


def PostAgentsAPI(path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    client = get_default_client()
    return client.post(path, data)


__all__ = ['SAPAgentAPIError', 'SAPAgentsClient', 'PostAgentsAPI', 'get_default_client']
