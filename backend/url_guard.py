"""Validation des URL à scanner (protection contre la SSRF).

Le scanner ouvre l'URL dans un vrai navigateur, côté serveur, puis renvoie des
extraits du HTML de la page. Sans contrôle, n'importe qui pourrait lui faire lire
une page interne (http://localhost:8000/admin, http://169.254.169.254/ qui expose
les identifiants cloud, un intranet...) et en récupérer le contenu.
"""

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURLError(ValueError):
    """URL refusée : schéma non autorisé, hôte introuvable ou adresse non publique."""


def normalize_url(raw: str) -> str:
    url = raw.strip()
    if "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Seules les adresses http et https peuvent être scannées.")
    if not parsed.hostname:
        raise UnsafeURLError("URL invalide.")
    return url


def _as_ip(address: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    ip = ipaddress.ip_address(address.split("%", 1)[0])  # retire l'éventuel « %scope » IPv6
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped  # ::ffff:127.0.0.1 est en réalité 127.0.0.1
    return ip


def resolve_public_ip(url: str, resolver=socket.getaddrinfo) -> str:
    """Résout l'hôte de l'URL et renvoie une adresse IP publique.

    Refuse l'URL si l'hôte est introuvable ou si UNE des adresses renvoyées n'est pas
    publique (privée, loopback, link-local, réservée, CGNAT...). L'adresse renvoyée sert
    à épingler la résolution dans Chrome, pour qu'un DNS qui change de réponse entre la
    vérification et le chargement (DNS rebinding) ne permette pas de contourner le contrôle.
    """
    host = urlparse(url).hostname
    if not host:
        raise UnsafeURLError("URL invalide.")
    try:
        infos = resolver(host, None)
    except (socket.gaierror, UnicodeError):
        raise UnsafeURLError(f"Nom de domaine introuvable : {host}")

    addresses = [_as_ip(info[4][0]) for info in infos]
    if not addresses:
        raise UnsafeURLError(f"Nom de domaine introuvable : {host}")
    for ip in addresses:
        if not ip.is_global or ip.is_multicast:
            raise UnsafeURLError("Cette adresse pointe vers un réseau interne : scan refusé.")
    return str(addresses[0])
