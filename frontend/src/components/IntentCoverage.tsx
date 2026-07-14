import type { IntentRow } from "../api/client";

const LABEL: Record<string, string> = {
  best_of: "Best-of",
  comparison: "Comparison",
  alternatives: "Alternatives",
  problem_first: "Problem-first",
  other: "Other",
};

export function IntentCoverage({ rows }: { rows: IntentRow[] }) {
  if (rows.length === 0) return <p className="muted">No prompts yet.</p>;
  return (
    <div className="intent">
      {rows.map((r) => (
        <div key={r.intent_type} className="intent-row">
          <div className="intent-name">{LABEL[r.intent_type] ?? r.intent_type}</div>
          <div className="intent-bar-track">
            <div className="intent-bar" style={{ width: `${r.coverage * 100}%` }} />
          </div>
          <div className="intent-val">
            {r.mentioned}/{r.total}
          </div>
        </div>
      ))}
    </div>
  );
}
