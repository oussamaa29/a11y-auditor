import os
import logging
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

from config import settings
from url_guard import resolve_public_ip

logger = logging.getLogger("scanner")

_AXE_PATH = os.path.join(os.path.dirname(__file__), "vendor", "axe.min.js")
with open(_AXE_PATH, encoding="utf-8") as f:
    AXE_SOURCE = f.read()

IMPACT_WEIGHT = {"critical": 10, "serious": 6, "moderate": 3, "minor": 1}
MAX_INSTANCES_PER_RULE = 5


def _build_driver(host: str, pinned_ip: str) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,900")
    # Chrome résout l'hôte principal vers l'adresse déjà validée, pas vers ce que
    # répondrait le DNS une seconde fois (protection contre le DNS rebinding).
    ip = f"[{pinned_ip}]" if ":" in pinned_ip else pinned_ip
    options.add_argument(f"--host-resolver-rules=MAP {host} {ip}")
    # Le bac à sable de Chrome reste actif, sauf dans un conteneur lancé en root où il
    # ne peut pas démarrer : il faut alors le désactiver explicitement.
    if settings.CHROME_NO_SANDBOX:
        options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def compute_score(violations: list) -> float:
    score = 100.0
    for v in violations:
        weight = IMPACT_WEIGHT.get(v.get("impact") or "minor", 1)
        instances = min(len(v.get("nodes", [])), MAX_INSTANCES_PER_RULE)
        score -= weight * instances
    return max(0.0, round(score, 1))


def count_by_impact(violations: list) -> dict:
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in violations:
        impact = v.get("impact") or "minor"
        if impact in counts:
            counts[impact] += 1
    return counts


def _format_target(target) -> str:
    # axe renvoie une liste de sélecteurs pour un élément dans une iframe ou un shadow DOM
    return " >> ".join(map(str, target)) if isinstance(target, list) else str(target)


def format_violations(violations_raw: list) -> list:
    return [
        {
            "id": v["id"],
            "impact": v.get("impact") or "minor",
            "description": v["description"],
            "help": v["help"],
            "help_url": v["helpUrl"],
            "tags": v.get("tags", []),
            "nodes": [
                {
                    "html": n.get("html", ""),
                    "target": [_format_target(t) for t in n.get("target", [])],
                    "failure_summary": n.get("failureSummary"),
                }
                for n in v.get("nodes", [])
            ],
        }
        for v in violations_raw
    ]


def run_scan(url: str, pinned_ip: str) -> dict:
    """Charge l'URL dans Chrome headless, injecte axe-core et renvoie un rapport structuré.

    Lève RuntimeError si la page ne charge pas ou si l'analyse échoue, et UnsafeURLError
    si la page a redirigé vers une adresse interne.
    """
    driver = _build_driver(urlparse(url).hostname, pinned_ip)
    try:
        driver.set_page_load_timeout(settings.SCAN_TIMEOUT)
        driver.set_script_timeout(settings.SCAN_TIMEOUT)
        try:
            driver.get(url)
        except WebDriverException as e:
            raise RuntimeError(f"Impossible de charger la page : {getattr(e, 'msg', None) or e}")

        # Une redirection peut mener vers un autre hôte : on revérifie l'adresse finale
        # avant de lire quoi que ce soit de la page.
        final_url = driver.current_url
        if urlparse(final_url).hostname != urlparse(url).hostname:
            resolve_public_ip(final_url)

        driver.execute_script(AXE_SOURCE)
        results = driver.execute_async_script(
            """
            var callback = arguments[arguments.length - 1];
            axe.run(document, {}).then(function(results){ callback(results); })
               .catch(function(err){ callback({error: String(err)}); });
            """
        )

        if not isinstance(results, dict):
            raise RuntimeError("Réponse inattendue d'axe-core.")
        if "error" in results and "violations" not in results:
            raise RuntimeError(f"Erreur pendant l'analyse axe-core : {results['error']}")

        violations = format_violations(results.get("violations", []))
        return {
            "score": compute_score(violations),
            "counts": count_by_impact(violations),
            "passes_count": len(results.get("passes", [])),
            "violations": violations,
        }
    finally:
        driver.quit()
