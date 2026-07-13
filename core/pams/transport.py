"""
core/pams/transport.py
======================
HTTP transport port for PAMS source adapters.

Source adapters never import ``requests`` directly — they depend on the
``HttpClient`` protocol. Production wiring injects ``RequestsHttpClient``; tests
inject ``FakeHttpClient`` so every source is testable with no network.

Centralizes the cross-cutting safety controls (timeout, response size cap) so no
individual adapter can forget them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Protocol
from urllib.parse import urlparse


class TransportError(RuntimeError):
    """Raised for network/transport failures (timeouts, connection errors, HTTP errors)."""


class HostNotAllowed(TransportError):
    """Raised when a request targets a host outside the configured allowlist (SSRF guard)."""


@dataclass
class HttpResponse:
    status: int
    text: str
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class HttpClient(Protocol):
    def get(self, url: str, *, timeout: float = 30.0) -> HttpResponse: ...


class RequestsHttpClient:
    """Default transport backed by ``requests`` with:
      * a hard response-size cap (no giant assemblies buffered),
      * an optional host allowlist (defense-in-depth SSRF guard),
      * bounded retries on transient failures (connection errors / timeouts / 5xx).
    """

    def __init__(
        self,
        max_bytes: int = 50 * 1024 * 1024,
        connect_timeout: float = 5.0,
        allowed_hosts: Optional[Iterable[str]] = None,
        max_retries: int = 2,
        backoff: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._max_bytes = max_bytes
        self._connect_timeout = connect_timeout
        self._allowed_hosts = {h.lower() for h in allowed_hosts} if allowed_hosts else None
        self._max_retries = max(0, int(max_retries))
        self._backoff = backoff
        self._sleep = sleep

    def _check_host(self, url: str) -> None:
        if self._allowed_hosts is None:
            return
        host = (urlparse(url).hostname or "").lower()
        if host not in self._allowed_hosts:
            raise HostNotAllowed(
                f"Refusing request to '{host}': not in the allowed hosts "
                f"({sorted(self._allowed_hosts)})."
            )

    def get(self, url: str, *, timeout: float = 30.0) -> HttpResponse:
        import requests  # imported lazily so PAMS core has no hard requests dep at import time

        self._check_host(url)

        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = requests.get(url, timeout=(self._connect_timeout, timeout), stream=True)
            except requests.RequestException as exc:  # connection reset / timeout / DNS
                last_exc = exc
                if attempt < self._max_retries:
                    self._sleep(self._backoff * (attempt + 1))
                    continue
                raise TransportError(f"Request to {url} failed after retries: {exc}") from exc

            # Retry transient server errors, but never 4xx (not-found/bad-request are final).
            if resp.status_code >= 500 and attempt < self._max_retries:
                resp.close()
                self._sleep(self._backoff * (attempt + 1))
                continue

            # Enforce the size cap while streaming so we never buffer a giant assembly.
            chunks, total = [], 0
            for chunk in resp.iter_content(chunk_size=65536, decode_unicode=False):
                if not chunk:
                    continue
                total += len(chunk)
                if total > self._max_bytes:
                    resp.close()
                    raise TransportError(
                        f"Response from {url} exceeds the {self._max_bytes} byte limit."
                    )
                chunks.append(chunk)
            body = b"".join(chunks)
            try:
                text = body.decode("utf-8", errors="replace")
            finally:
                resp.close()
            return HttpResponse(status=resp.status_code, text=text, url=url)

        # Only reachable if the loop exhausted retries on 5xx without returning.
        raise TransportError(f"Request to {url} failed after retries: last error {last_exc}")


class FakeHttpClient:
    """Deterministic transport for tests. Maps URL -> HttpResponse (or a callable)."""

    def __init__(self, responses: Optional[Dict[str, object]] = None):
        self._responses = responses or {}
        self.calls: list[str] = []

    def register(self, url: str, response: object) -> None:
        self._responses[url] = response

    def get(self, url: str, *, timeout: float = 30.0) -> HttpResponse:
        self.calls.append(url)
        if url not in self._responses:
            raise TransportError(f"FakeHttpClient has no registered response for {url}")
        r = self._responses[url]
        if callable(r):
            r = r(url)
        if isinstance(r, HttpResponse):
            return r
        if isinstance(r, tuple):  # (status, text)
            return HttpResponse(status=r[0], text=r[1], url=url)
        return HttpResponse(status=200, text=str(r), url=url)


__all__ = [
    "HttpClient", "HttpResponse", "RequestsHttpClient", "FakeHttpClient",
    "TransportError", "HostNotAllowed",
]
