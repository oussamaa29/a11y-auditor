import threading

import pytest

import main
from url_guard import UnsafeURLError

FAKE_REPORT = {
    "score": 84.0,
    "counts": {"critical": 1, "serious": 1, "moderate": 0, "minor": 0},
    "passes_count": 30,
    "violations": [{
        "id": "image-alt",
        "impact": "critical",
        "description": "Les images doivent avoir un texte alternatif",
        "help": "Images must have alternate text",
        "help_url": "https://dequeuniversity.com/rules/axe/image-alt",
        "tags": ["wcag2a"],
        "nodes": [{"html": "<img src='logo.png'>", "target": ["img"], "failure_summary": "Fix this"}],
    }],
}


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(main, "resolve_public_ip", lambda url: "93.184.215.14")


@pytest.fixture
def fake_scan(monkeypatch, public_dns):
    calls = []

    def run(url, pinned_ip):
        calls.append((url, pinned_ip))
        return FAKE_REPORT

    monkeypatch.setattr(main, "run_scan", run)
    return calls


def test_scan_is_created_and_listed(client, fake_scan):
    resp = client.post("/api/scans", json={"url": "example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["url"] == "https://example.com"
    assert body["score"] == 84.0
    assert body["created_at"].endswith("+00:00")  # fuseau explicite pour le navigateur
    assert body["violations"][0]["id"] == "image-alt"
    # Chrome reçoit l'adresse déjà validée
    assert fake_scan == [("https://example.com", "93.184.215.14")]

    listed = client.get("/api/scans").json()
    assert [s["id"] for s in listed] == [body["id"]]
    assert client.get(f"/api/scans/{body['id']}").json()["violations"] == body["violations"]


def test_internal_url_is_refused_before_launching_chrome(client, monkeypatch):
    monkeypatch.setattr(main, "run_scan", lambda *a: pytest.fail("Chrome ne doit pas être lancé"))
    resp = client.post("/api/scans", json={"url": "http://127.0.0.1:8020/api/scans"})
    assert resp.status_code == 400
    assert "réseau interne" in resp.json()["detail"]
    assert client.get("/api/scans").json() == []


def test_non_http_scheme_is_refused(client):
    assert client.post("/api/scans", json={"url": "file:///etc/passwd"}).status_code == 400


def test_redirect_to_internal_address_is_refused_and_not_stored(client, monkeypatch, public_dns):
    def redirected(url, pinned_ip):
        raise UnsafeURLError("Cette adresse pointe vers un réseau interne : scan refusé.")

    monkeypatch.setattr(main, "run_scan", redirected)
    assert client.post("/api/scans", json={"url": "example.com"}).status_code == 400
    assert client.get("/api/scans").json() == []


def test_failed_page_load_is_recorded_with_its_error(client, monkeypatch, public_dns):
    def failing(url, pinned_ip):
        raise RuntimeError("Impossible de charger la page : timeout")

    monkeypatch.setattr(main, "run_scan", failing)
    resp = client.post("/api/scans", json={"url": "example.com"})
    assert resp.status_code == 502
    [scan] = client.get("/api/scans").json()
    assert scan["error"] == "Impossible de charger la page : timeout"


def test_too_many_concurrent_scans_returns_503(client, monkeypatch, fake_scan):
    busy = threading.BoundedSemaphore(1)
    busy.acquire()
    monkeypatch.setattr(main, "_scan_slots", busy)
    resp = client.post("/api/scans", json={"url": "example.com"})
    assert resp.status_code == 503
    assert fake_scan == []


def test_slot_is_released_after_a_failure(client, monkeypatch, public_dns):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(main, "_scan_slots", slots)
    monkeypatch.setattr(main, "run_scan", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    client.post("/api/scans", json={"url": "example.com"})
    assert slots.acquire(blocking=False)


def test_list_is_paginated(client, fake_scan):
    for _ in range(3):
        client.post("/api/scans", json={"url": "example.com"})
    assert len(client.get("/api/scans?limit=2").json()) == 2
    assert len(client.get("/api/scans?limit=2&offset=2").json()) == 1
    assert client.get("/api/scans?limit=0").status_code == 422


def test_delete_and_404(client, fake_scan):
    scan_id = client.post("/api/scans", json={"url": "example.com"}).json()["id"]
    assert client.delete(f"/api/scans/{scan_id}").status_code == 204
    assert client.get(f"/api/scans/{scan_id}").status_code == 404
    assert client.delete(f"/api/scans/{scan_id}").status_code == 404
