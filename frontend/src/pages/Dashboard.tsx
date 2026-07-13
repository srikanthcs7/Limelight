import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { VisibilityTrend } from "../charts/VisibilityTrend";

export function Dashboard() {
  const qc = useQueryClient();
  const brandsQ = useQuery({ queryKey: ["brands"], queryFn: api.brands });
  const [brandId, setBrandId] = useState<string | null>(null);
  const [token, setToken] = useState<string>(
    () => localStorage.getItem("limelight_admin_token") ?? "",
  );

  const activeBrandId = brandId ?? brandsQ.data?.[0]?.id ?? null;

  const scoresQ = useQuery({
    queryKey: ["scores", activeBrandId],
    queryFn: () => api.scores(activeBrandId!),
    enabled: !!activeBrandId,
  });
  const runsQ = useQuery({
    queryKey: ["runs", activeBrandId],
    queryFn: () => api.runs(activeBrandId!),
    enabled: !!activeBrandId,
  });

  const saveToken = (v: string) => {
    setToken(v);
    localStorage.setItem("limelight_admin_token", v);
  };

  const seedM = useMutation({
    mutationFn: () => api.seed(token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brands"] }),
  });
  const runM = useMutation({
    mutationFn: () => api.triggerRun(activeBrandId!, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs", activeBrandId] });
      qc.invalidateQueries({ queryKey: ["scores", activeBrandId] });
    },
  });

  const latest = scoresQ.data?.[scoresQ.data.length - 1];
  const brand = brandsQ.data?.find((b) => b.id === activeBrandId);
  const noBrands = brandsQ.data && brandsQ.data.length === 0;
  const busy = seedM.isPending || runM.isPending;
  const error = seedM.error ?? runM.error;

  return (
    <div className="container">
      <h1>Limelight — AI Visibility Tracker</h1>

      <div className="card admin-bar">
        <input
          type="password"
          placeholder="Admin token"
          value={token}
          onChange={(e) => saveToken(e.target.value)}
          style={{ minWidth: 220 }}
        />
        {noBrands && (
          <button disabled={!token || busy} onClick={() => seedM.mutate()}>
            {seedM.isPending ? "Seeding…" : "Seed GetQuizSolve"}
          </button>
        )}
        {activeBrandId && (
          <button disabled={!token || busy} onClick={() => runM.mutate()}>
            {runM.isPending ? "Running… (~10–30s)" : "Run now"}
          </button>
        )}
        {error && <span className="err">{String(error.message ?? error)}</span>}
        {runM.isSuccess && !busy && (
          <span className="ok">Ran {runM.data.runs} prompt(s).</span>
        )}
      </div>

      {brandsQ.isLoading && <p className="muted">Loading brands…</p>}
      {brandsQ.data && brandsQ.data.length > 0 && (
        <select value={activeBrandId ?? ""} onChange={(e) => setBrandId(e.target.value)}>
          {brandsQ.data.map((b) => (
            <option key={b.id} value={b.id}>
              {b.display_name} ({b.domain})
            </option>
          ))}
        </select>
      )}

      <div className="card">
        <h2>Visibility score {brand ? `· ${brand.display_name}` : ""}</h2>
        <div className="score-hero">{latest ? latest.visibility_score : "—"}</div>
        {latest && (
          <div className="metrics">
            <span className="metric">
              Mention rate <b>{(latest.mention_rate * 100).toFixed(0)}%</b>
            </span>
            <span className="metric">
              Share of voice <b>{(latest.share_of_voice * 100).toFixed(0)}%</b>
            </span>
            <span className="metric">
              Citation rate <b>{(latest.citation_rate * 100).toFixed(0)}%</b>
            </span>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Visibility over time</h2>
        <VisibilityTrend scores={scoresQ.data ?? []} />
      </div>

      <div className="card">
        <h2>Recent runs</h2>
        {runsQ.data && runsQ.data.length === 0 && <p className="muted">No runs yet.</p>}
        {runsQ.data?.map((run) => (
          <div key={run.id} style={{ marginBottom: 16 }}>
            <div className="muted">{new Date(run.run_at).toLocaleString()}</div>
            <p>{run.answer_text.slice(0, 220)}…</p>
            <div>
              {run.mentions.map((m) => (
                <span
                  key={m.entity_name}
                  className={m.is_tracked_brand ? "brand-tag" : "muted"}
                  style={{ marginRight: 12 }}
                >
                  {m.entity_name} #{m.position}
                </span>
              ))}
            </div>
            <div className="muted" style={{ marginTop: 4 }}>
              cited: {[...new Set(run.citations.map((c) => c.domain))].join(", ") || "none"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
