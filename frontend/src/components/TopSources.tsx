import type { SourceRow } from "../api/client";

export function TopSources({ rows }: { rows: SourceRow[] }) {
  if (rows.length === 0) return <p className="muted">No citations captured yet.</p>;
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th>Source domain</th>
          <th style={{ textAlign: "right" }}>Citations</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.domain}>
            <td>{r.domain}</td>
            <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{r.citations}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
