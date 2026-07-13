"""
Tests for PAMS #6 hardening: transport host allowlist, bounded retries, and the
structure download cache. No real network — requests.get is monkeypatched.
"""

import json

import pytest

from core.pams.transport import (
    RequestsHttpClient, HostNotAllowed, TransportError, HttpResponse, FakeHttpClient,
)
from core.pams.cache import FileSystemStructureCache, NullStructureCache
from core.pams.sources.rcsb import RCSBSource, RCSB_HOSTS
from core.pams.sources.base import SourceRequest
from core.pams import _remote_host_allowlist


# ── Host allowlist (SSRF guard) ──────────────────────────────────────

def test_host_allowlist_blocks_unlisted_before_network():
    client = RequestsHttpClient(allowed_hosts={"files.rcsb.org"})
    with pytest.raises(HostNotAllowed):
        client.get("https://evil.example.com/x")   # raises before any network call


def test_host_allowlist_permits_listed_host():
    client = RequestsHttpClient(allowed_hosts={"files.rcsb.org"})
    client._check_host("https://files.rcsb.org/download/4duh.pdb")  # no raise


def test_no_allowlist_allows_any_host():
    RequestsHttpClient()._check_host("https://anything.example.com")  # no raise


def test_registry_allowlist_includes_rcsb_hosts():
    assert _remote_host_allowlist() >= set(RCSB_HOSTS)


# ── Bounded retries ──────────────────────────────────────────────────

class _FakeResp:
    def __init__(self, status, body=b"DATA"):
        self.status_code = status
        self._body = body

    def iter_content(self, chunk_size=65536, decode_unicode=False):
        yield self._body

    def close(self):
        pass


def test_retry_then_success(monkeypatch):
    import requests
    calls = {"n": 0}

    def fake_get(url, timeout=None, stream=False):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("transient")
        return _FakeResp(200)

    monkeypatch.setattr(requests, "get", fake_get)
    client = RequestsHttpClient(max_retries=2, sleep=lambda s: None)
    resp = client.get("https://files.rcsb.org/download/4duh.pdb")
    assert resp.status == 200 and calls["n"] == 3


def test_retry_exhausted_raises(monkeypatch):
    import requests

    def always_fail(url, timeout=None, stream=False):
        raise requests.Timeout("t")

    monkeypatch.setattr(requests, "get", always_fail)
    client = RequestsHttpClient(max_retries=2, sleep=lambda s: None)
    with pytest.raises(TransportError):
        client.get("https://files.rcsb.org/x")


def test_5xx_is_retried(monkeypatch):
    import requests
    calls = {"n": 0}

    def fake_500(url, timeout=None, stream=False):
        calls["n"] += 1
        return _FakeResp(503)

    monkeypatch.setattr(requests, "get", fake_500)
    client = RequestsHttpClient(max_retries=1, sleep=lambda s: None)
    resp = client.get("https://files.rcsb.org/x")
    assert resp.status == 503 and calls["n"] == 2   # initial + 1 retry


# ── Structure cache ──────────────────────────────────────────────────

def test_filesystem_cache_roundtrip(tmp_path):
    cache = FileSystemStructureCache(str(tmp_path))
    assert cache.get("k") is None
    cache.put("k", "STRUCTURE")
    assert cache.get("k") == "STRUCTURE"


def test_null_cache_is_noop():
    c = NullStructureCache()
    c.put("k", "v")
    assert c.get("k") is None


def _rcsb_http():
    http = FakeHttpClient()
    http.register("https://files.rcsb.org/download/4duh.pdb", HttpResponse(200, "ATOM  ...\n", "u"))
    meta = json.dumps({"struct": {"title": "T"}, "rcsb_entry_info": {}, "exptl": [],
                       "rcsb_accession_info": {}})
    http.register("https://data.rcsb.org/rest/v1/core/entry/4duh", HttpResponse(200, meta, "u"))
    return http


def test_rcsb_uses_cache_on_second_fetch(tmp_path):
    http = _rcsb_http()
    src = RCSBSource(http, cache=FileSystemStructureCache(str(tmp_path)))

    first = src.fetch(SourceRequest(source="rcsb", identifier="4DUH"))
    second = src.fetch(SourceRequest(source="rcsb", identifier="4DUH"))

    assert first.cached is False and second.cached is True
    # The structure file was downloaded exactly once (metadata is not cached).
    assert http.calls.count("https://files.rcsb.org/download/4duh.pdb") == 1
