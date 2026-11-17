from scanner import compute_score, count_by_impact, format_violations


def violation(impact, nodes=1):
    return {"impact": impact, "nodes": [{}] * nodes}


def test_perfect_score_without_violations():
    assert compute_score([]) == 100.0


def test_penalty_depends_on_severity():
    assert compute_score([violation("critical")]) == 90.0
    assert compute_score([violation("serious")]) == 94.0
    assert compute_score([violation("moderate")]) == 97.0
    assert compute_score([violation("minor")]) == 99.0


def test_missing_impact_counts_as_minor():
    assert compute_score([violation(None)]) == 99.0


def test_occurrences_are_capped_at_five_per_rule():
    assert compute_score([violation("serious", nodes=50)]) == 100 - 6 * 5


def test_score_never_goes_below_zero():
    assert compute_score([violation("critical", nodes=5)] * 5) == 0.0


def test_count_by_impact():
    counts = count_by_impact([violation("critical"), violation("critical"), violation(None)])
    assert counts == {"critical": 2, "serious": 0, "moderate": 0, "minor": 1}


def test_format_violations_flattens_iframe_and_shadow_dom_targets():
    raw = [{
        "id": "color-contrast",
        "impact": "serious",
        "description": "d",
        "help": "h",
        "helpUrl": "https://dequeuniversity.com/rules/axe/color-contrast",
        "nodes": [{"html": "<p>", "target": [["iframe#pub", "p.note"], "#main"], "failureSummary": "f"}],
    }]
    node = format_violations(raw)[0]["nodes"][0]
    assert node["target"] == ["iframe#pub >> p.note", "#main"]
    assert format_violations(raw)[0]["tags"] == []
