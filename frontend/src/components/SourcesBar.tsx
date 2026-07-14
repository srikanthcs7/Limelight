import type { SourceRow } from "../api/client";

export function SourcesBar({ rows }: { rows: SourceRow[] }) {
  if (rows.length === 0) return <p className="muted">No citations captured yet.</p>;
  const max = Math.max(...rows.map((r) => r.citations), 1);
  return (
    <div className="src">
      {rows.map((r) => (
        <div key={r.domain} className="src-row">
          <div className="src-name" title={r.domain}>
            {r.domain}
          </div>
          <div className="src-bar-track">
            <div className="src-bar" style={{ width: `${(r.citations / max) * 100}%` }} />
          </div>
          <div className="src-val">{r.citations}</div>
        </div>
      ))}
    </div>
  );
}
