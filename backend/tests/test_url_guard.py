import socket

import pytest

from tests.helpers import fake_resolver
from url_guard import UnsafeURLError, normalize_url, resolve_public_ip


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("example.com", "https://example.com"),
        ("  example.com/page  ", "https://example.com/page"),
        ("http://example.com", "http://example.com"),
        ("HTTPS://example.com", "HTTPS://example.com"),
        ("localhost:8000", "https://localhost:8000"),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw", ["file:///etc/passwd", "ftp://example.com", "javascript://alert(1)", "https://", ""]
)
def test_normalize_url_rejects_other_schemes_and_empty_hosts(raw):
    with pytest.raises(UnsafeURLError):
        normalize_url(raw)


def test_public_address_is_accepted_and_returned():
    assert resolve_public_ip("https://example.com", fake_resolver("93.184.215.14")) == "93.184.215.14"


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",        # loopback
        "10.0.0.5",         # réseau privé
        "172.16.3.4",
        "192.168.1.10",
        "169.254.169.254",  # métadonnées cloud (AWS, GCP, Azure)
        "100.64.0.1",       # CGNAT
        "0.0.0.0",
        "224.0.0.1",        # multicast
        "::1",
        "fd00::1",          # IPv6 privée
        "fe80::1%eth0",     # IPv6 link-local avec scope
        "::ffff:127.0.0.1",  # IPv4 encapsulée dans de l'IPv6
    ],
)
def test_internal_addresses_are_refused(address):
    with pytest.raises(UnsafeURLError):
        resolve_public_ip("https://intranet.example", fake_resolver(address))


def test_refused_if_any_resolved_address_is_internal():
    resolver = fake_resolver("93.184.215.14", "10.0.0.1")
    with pytest.raises(UnsafeURLError):
        resolve_public_ip("https://example.com", resolver)


def test_unknown_host_is_refused():
    def failing_resolver(host, port):
        raise socket.gaierror("introuvable")

    with pytest.raises(UnsafeURLError, match="introuvable"):
        resolve_public_ip("https://nexiste-pas.invalid", failing_resolver)


def test_ip_literals_are_checked_with_the_real_resolver():
    # Pas de réseau : getaddrinfo renvoie directement une IP littérale
    with pytest.raises(UnsafeURLError):
        resolve_public_ip("http://127.0.0.1:8000/admin")
    with pytest.raises(UnsafeURLError):
        resolve_public_ip("http://[::1]/")
