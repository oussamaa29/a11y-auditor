import { useEffect, useState } from "react";
import "./App.css";
import type { ScanDetail, ScanSummary } from "./types";
import { api } from "./api";
import ViolationCard from "./components/ViolationCard";

function scoreTier(score: number): "good" | "ok" | "bad" {
  if (score >= 85) return "good";
  if (score >= 60) return "ok";
  return "bad";
}

function App() {
  const [url, setUrl] = useState("");
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ScanSummary[]>([]);
  const [active, setActive] = useState<ScanDetail | null>(null);

  async function loadHistory() {
    try {
      setHistory(await api.listScans());
    } catch {
      // history is non-critical; ignore silently if the backend is briefly unavailable
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  async function handleScan(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setScanning(true);
    setError(null);
    try {
      const result = await api.runScan(url.trim());
      setActive(result);
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setScanning(false);
    }
  }

  async function openHistoryItem(id: number) {
    try {
      setActive(await api.getScan(id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }

  const sortedViolations = active
    ? [...active.violations].sort((a, b) => {
        const order = { critical: 0, serious: 1, moderate: 2, minor: 3 };
        return order[a.impact] - order[b.impact];
      })
    : [];

  return (
    <div className="app">
      <header className="topbar">
        <h1>Auditeur d'accessibilité web</h1>
        <p>Analyse RGAA / WCAG basée sur axe-core</p>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <form className="scan-form" onSubmit={handleScan}>
            <label htmlFor="url">URL à analyser</label>
            <input
              id="url"
              type="text"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button type="submit" className="btn primary" disabled={scanning}>
              {scanning ? "Analyse en cours…" : "Lancer l'audit"}
            </button>
          </form>

          <div className="history">
            <h2>Historique</h2>
            <div className="history-list">
              {history.length === 0 && <p className="history-empty">Aucun audit pour l'instant.</p>}
              {history.map((h) => (
                <button
                  key={h.id}
                  className={`history-item ${active?.id === h.id ? "active" : ""}`}
                  onClick={() => openHistoryItem(h.id)}
                  type="button"
                >
                  <span className="hi-url">{h.url.replace(/^https?:\/\//, "")}</span>
                  {h.error ? (
                    <span className="hi-score" style={{ background: "var(--critical-soft)", color: "var(--critical)" }}>err</span>
                  ) : (
                    <span className={`hi-score score-ring-mini`} style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>
                      {Math.round(h.score)}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <main className="main">
          {error && <div className="error-banner">{error}</div>}

          {!active && !error && (
            <div className="empty-state">
              <p>Colle une URL à gauche et lance un audit pour voir le rapport d'accessibilité complet.</p>
            </div>
          )}

          {active && !active.error && (
            <>
              <div className="result-head">
                <div className={`score-ring ${scoreTier(active.score)}`}>{Math.round(active.score)}</div>
                <div>
                  <div className="result-url">{active.url}</div>
                  <div className="result-date">{new Date(active.created_at).toLocaleString("fr-FR")}</div>
                </div>
              </div>

              <div className="counts-row">
                <div className="count-pill critical"><div className="n">{active.critical_count}</div><div className="l">Critique</div></div>
                <div className="count-pill serious"><div className="n">{active.serious_count}</div><div className="l">Sérieux</div></div>
                <div className="count-pill moderate"><div className="n">{active.moderate_count}</div><div className="l">Modéré</div></div>
                <div className="count-pill minor"><div className="n">{active.minor_count}</div><div className="l">Mineur</div></div>
                <div className="count-pill passes"><div className="n">{active.passes_count}</div><div className="l">Tests réussis</div></div>
              </div>

              <div className="violations">
                <h2>Violations détectées</h2>
                {sortedViolations.length === 0 ? (
                  <div className="no-violations">Aucune violation détectée par axe-core sur cette page. 🎉</div>
                ) : (
                  sortedViolations.map((v) => <ViolationCard key={v.id} violation={v} />)
                )}
              </div>
            </>
          )}

          {active && active.error && (
            <div className="error-banner">{active.error}</div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
