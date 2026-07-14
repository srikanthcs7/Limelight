import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Run } from "../api/client";

export function RunCard({ brandId, run }: { brandId: string; run: Run }) {
  const [open, setOpen] = useState(false);
  const detailQ = useQuery({
    queryKey: ["run-detail", run.id],
    queryFn: () => api.runDetail(brandId, run.id),
    enabled: open,
  });

  const domains = [...new Set(run.citations.map((c) => c.domain))];

  return (
    <div className="run">
      <div className="run-time">{new Date(run.run_at).toLocaleString()}</div>
      <p className="run-answer">{run.answer_text ? run.answer_text.slice(0, 240) + "…" : "(no answer / engine returned nothing)"}</p>
      <div className="chips">
        {run.mentions.length === 0 && <span className="muted">No tracked brands mentioned</span>}
        {run.mentions.map((m) => (
          <span key={m.entity_name} className={m.is_tracked_brand ? "chip brand" : "chip"}>
            {m.sentiment && <i className={`sdot ${m.sentiment}`} />}
            {m.entity_name} · #{m.position}
          </span>
        ))}
      </div>
      <div className="cited">Cited: {domains.join(", ") || "none"}</div>

      <button className="link-btn" onClick={() => setOpen((o) => !o)}>
        {open ? "▾ Hide raw response" : "▸ View raw response"}
      </button>
      {open && (
        <div className="raw-box">
          {detailQ.isLoading && <span className="muted">Loading…</span>}
          {detailQ.error && <span className="err">{String((detailQ.error as Error).message)}</span>}
          {detailQ.data && (
            <>
              {run.citations.length > 0 && (
                <div className="raw-links">
                  {run.citations.map((c, i) => (
                    <a key={i} href={c.url} target="_blank" rel="noreferrer">
                      {c.domain}
                    </a>
                  ))}
                </div>
              )}
              <pre>{JSON.stringify(detailQ.data.raw_response_json, null, 2)}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}
