"""Small dependency-free JSON HTTP client."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class JsonHttpClient:
    """HTTP GET client with explicit timeout and user agent."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30,
        user_agent: str = "loadshift-uk/0.1",
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str | int | float] | None = None,
    ) -> Mapping[str, Any]:
        query = urlencode(params or {})
        request_url = f"{url}?{query}" if query else url
        request = Request(
            request_url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.load(response)
        if not isinstance(payload, Mapping):
            raise ValueError("API response must be a JSON object")
        return payload
