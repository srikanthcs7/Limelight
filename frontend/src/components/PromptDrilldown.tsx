import type { PromptRow } from "../api/client";

const INTENT_LABEL: Record<string, string> = {
  best_of: "Best-of",
  comparison: "Comparison",
  alternatives: "Alternatives",
  problem_first: "Problem",
};

export function PromptDrilldown({ rows }: { rows: PromptRow[] }) {
  if (rows.length === 0) return <p className="muted">No prompts yet — generate some in Settings.</p>;
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th>Prompt</th>
          <th>Intent</th>
          <th style={{ textAlign: "center" }}>You</th>
          <th style={{ textAlign: "center" }}>Runs</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.prompt_id}>
            <td>
              {r.text}
              {!r.brand_mentioned && r.competitors_present.length > 0 && (
                <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                  competitors here: {r.competitors_present.slice(0, 3).join(", ")}
                </div>
              )}
            </td>
            <td>
              <span className="chip">{r.intent_type ? INTENT_LABEL[r.intent_type] ?? r.intent_type : "—"}</span>
            </td>
            <td style={{ textAlign: "center" }}>
              {r.brand_mentioned ? (
                <span className="ok">#{r.position}</span>
              ) : (
                <span className="err">absent</span>
              )}
            </td>
            <td style={{ textAlign: "center", color: "var(--ink-3)" }}>{r.runs_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
