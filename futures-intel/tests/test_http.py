from __future__ import annotations

import json
from io import BytesIO

import pytest

from futures_intel.config import load_compliance
from futures_intel.http import BudgetExceeded, ComplianceError, PoliteClient, RemoteStop


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args) -> None:
        return None


def test_cache_avoids_second_network_call(tmp_path) -> None:
    calls = []

    def opener(request, timeout):  # noqa: ARG001
        calls.append(request.full_url)
        return _FakeResponse({"ok": True})

    client = PoliteClient(load_compliance(), tmp_path / "cache", opener=opener, sleeper=lambda _: None)
    first = client.get_json("https://example.test/api", {"q": "1"})
    second = client.get_json("https://example.test/api", {"q": "1"})
    assert first.cached is False
    assert second.cached is True
    assert client.requests_used == 1
    assert len(calls) == 1
    assert "example.test" in first.url


def test_identifiable_user_agent(tmp_path) -> None:
    seen = {}

    def opener(request, timeout):  # noqa: ARG001
        seen["ua"] = request.get_header("User-agent")
        return _FakeResponse({"ok": True})

    PoliteClient(load_compliance(), tmp_path / "cache", opener=opener, sleeper=lambda _: None).get_json(
        "https://example.test/api"
    )
    assert "personal-research" in seen["ua"]
    assert "Mozilla" not in seen["ua"]


def test_budget_and_offline(tmp_path) -> None:
    compliance = load_compliance()

    def opener(request, timeout):  # noqa: ARG001
        return _FakeResponse({"ok": True})

    client = PoliteClient(compliance, tmp_path / "cache", opener=opener, sleeper=lambda _: None)
    client.requests_used = compliance.max_requests_per_run
    with pytest.raises(BudgetExceeded):
        client.get_json("https://example.test/new")

    offline = PoliteClient(
        compliance, tmp_path / "offline", allow_network=False, opener=opener, sleeper=lambda _: None
    )
    with pytest.raises(ComplianceError):
        offline.get_json("https://example.test/api")


def test_stop_on_forbidden(tmp_path) -> None:
    def opener(request, timeout):  # noqa: ARG001
        class _Resp(BytesIO):
            status = 403

            def read(self) -> bytes:
                return b"forbidden"

        return _Resp()

    client = PoliteClient(load_compliance(), tmp_path / "cache", opener=opener, sleeper=lambda _: None)
    with pytest.raises(RemoteStop):
        client.get_json("https://example.test/api")
