import type { ShareRow } from "../api/client";

export function CompetitorTable({ rows }: { rows: ShareRow[] }) {
  if (rows.length === 0) return <p className="muted">No mentions yet.</p>;
  const max = Math.max(...rows.map((r) => r.share), 0.0001);
  return (
    <div className="sov">
      {rows.map((r) => (
        <div key={r.entity_name} className="sov-row">
          <div className="sov-name">
            {r.is_tracked_brand ? <b className="brand-tag">{r.entity_name}</b> : r.entity_name}
          </div>
          <div className="sov-bar-track">
            <div
              className={r.is_tracked_brand ? "sov-bar brand" : "sov-bar"}
              style={{ width: `${(r.share / max) * 100}%` }}
            />
          </div>
          <div className="sov-val">{(r.share * 100).toFixed(0)}%</div>
        </div>
      ))}
    </div>
  );
}
