import os
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

from config import settings

logger = logging.getLogger("scanner")

_AXE_PATH = os.path.join(os.path.dirname(__file__), "vendor", "axe.min.js")
with open(_AXE_PATH, encoding="utf-8") as f:
    AXE_SOURCE = f.read()

IMPACT_WEIGHT = {"critical": 10, "serious": 6, "moderate": 3, "minor": 1}
MAX_INSTANCES_PER_RULE = 5


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1366,900")
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


def run_scan(url: str) -> dict:
    """Loads the URL in headless Chrome, injects axe-core, and returns a
    structured accessibility report. Raises RuntimeError on navigation/scan failure."""
    driver = _build_driver()
    try:
        driver.set_page_load_timeout(settings.SCAN_TIMEOUT)
        driver.set_script_timeout(settings.SCAN_TIMEOUT)
        try:
            driver.get(url)
        except WebDriverException as e:
            raise RuntimeError(f"Impossible de charger la page : {e.msg if hasattr(e, 'msg') else str(e)}")

        driver.execute_script(AXE_SOURCE)
        results = driver.execute_async_script(
            """
            var callback = arguments[arguments.length - 1];
            axe.run(document, {}).then(function(results){ callback(results); })
               .catch(function(err){ callback({error: String(err)}); });
            """
        )

        if not isinstance(results, dict) or "error" in results and "violations" not in results:
            raise RuntimeError(results.get("error", "Erreur inconnue pendant l'analyse axe-core"))

        violations_raw = results.get("violations", [])
        violations = [
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
                        "target": n.get("target", []),
                        "failure_summary": n.get("failureSummary"),
                    }
                    for n in v.get("nodes", [])
                ],
            }
            for v in violations_raw
        ]

        return {
            "score": compute_score(violations),
            "counts": count_by_impact(violations),
            "passes_count": len(results.get("passes", [])),
            "violations": violations,
        }
    finally:
        driver.quit()
