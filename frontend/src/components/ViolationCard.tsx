import { useState } from "react";
import type { Violation } from "../types";

const IMPACT_LABEL: Record<string, string> = {
  critical: "Critique",
  serious: "Sérieux",
  moderate: "Modéré",
  minor: "Mineur",
};

export default function ViolationCard({ violation }: { violation: Violation }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="violation">
      <div className="violation-head" onClick={() => setOpen((o) => !o)}>
        <span className={`badge ${violation.impact}`}>{IMPACT_LABEL[violation.impact] ?? violation.impact}</span>
        <span className="vh-text">{violation.help}</span>
        <span className="vh-count">{violation.nodes.length} élément{violation.nodes.length > 1 ? "s" : ""}</span>
      </div>
      {open && (
        <div className="violation-body">
          <p>{violation.description}</p>
          <a href={violation.help_url} target="_blank" rel="noopener noreferrer">
            Documentation de la règle ↗
          </a>
          {violation.nodes.map((node, i) => (
            <div className="node-item" key={i}>
              <div className="target">{node.target.join(" ")}</div>
              <pre>{node.html}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
