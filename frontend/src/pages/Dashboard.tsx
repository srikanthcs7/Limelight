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
  const [showSettings, setShowSettings] = useState(false);

  const activeBrandId = brandId ?? brandsQ.data?.[0]?.id ?? null;
  const brand = brandsQ.data?.find((b) => b.id === activeBrandId);

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
  const promptsQ = useQuery({
    queryKey: ["prompts", activeBrandId],
    queryFn: () => api.prompts(activeBrandId!),
    enabled: !!activeBrandId,
  });

  const saveToken = (v: string) => {
    setToken(v);
    localStorage.setItem("limelight_admin_token", v);
  };

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["runs", activeBrandId] });
    qc.invalidateQueries({ queryKey: ["scores", activeBrandId] });
    qc.invalidateQueries({ queryKey: ["prompts", activeBrandId] });
  };

  const seedM = useMutation({
    mutationFn: () => api.seed(token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brands"] }),
  });
  const runM = useMutation({ mutationFn: () => api.triggerRun(activeBrandId!, token), onSuccess: refresh });
  const genM = useMutation({
    mutationFn: () => api.generatePrompts(activeBrandId!, token),
    onSuccess: refresh,
  });

  const latest = scoresQ.data?.[scoresQ.data.length - 1];
  const noBrands = brandsQ.data && brandsQ.data.length === 0;
  const busy = seedM.isPending || runM.isPending || genM.isPending;
  const error = seedM.error ?? runM.error ?? genM.error;
  const activePrompts = promptsQ.data?.filter((p) => p.active).length ?? 0;

  return (
    <div className="container">
      <div className="masthead">
        <div>
          <h1 className="title">Limelight</h1>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {brandsQ.data && brandsQ.data.length > 0 && (
            <select value={activeBrandId ?? ""} onChange={(e) => setBrandId(e.target.value)}>
              {brandsQ.data.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.display_name}
                </option>
              ))}
            </select>
          )}
          <button className="btn secondary" onClick={() => setShowSettings((s) => !s)}>
            {showSettings ? "Done" : "Settings"}
          </button>
        </div>
      </div>
      <p className="subtitle">AI visibility for {brand ? brand.display_name : "your brand"} on ChatGPT search</p>

      {brand && (
        <div className="meta-row">
          <span className="pill">🔗 {brand.domain}</span>
          {brand.category && <span className="pill">🏷 {brand.category}</span>}
          <span className="pill">💬 {activePrompts} prompts</span>
          <span className="pill">🤖 ChatGPT</span>
          <span className="pill">🥇 {brand.competitors.length} competitors</span>
        </div>
      )}

      {(showSettings || noBrands) && (
        <div className="card">
          <h2>Controls</h2>
          <div className="toolbar">
            <input
              type="password"
              placeholder="Admin token"
              value={token}
              onChange={(e) => saveToken(e.target.value)}
            />
            {noBrands && (
              <button className="btn" disabled={!token || busy} onClick={() => seedM.mutate()}>
                {seedM.isPending ? "Seeding…" : "Seed GetQuizSolve"}
              </button>
            )}
            {activeBrandId && (
              <>
                <button className="btn" disabled={!token || busy} onClick={() => runM.mutate()}>
                  {runM.isPending ? "Running… (~10–30s)" : "Run now"}
                </button>
                <button
                  className="btn secondary"
                  disabled={!token || busy}
                  onClick={() => genM.mutate()}
                >
                  {genM.isPending ? "Generating…" : "Generate prompts"}
                </button>
              </>
            )}
            {error && <span className="err">{String((error as Error).message ?? error)}</span>}
            {runM.isSuccess && !busy && <span className="ok">Ran {runM.data.runs} prompt(s).</span>}
            {genM.isSuccess && !busy && (
              <span className="ok">Added {genM.data.added_prompts} prompts.</span>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Visibility score</h2>
        <div className="hero">
          <span className="hero-score">{latest ? latest.visibility_score : "—"}</span>
          <span className="hero-out-of">/ 100</span>
        </div>
        <div className="kpis">
          <div className="kpi">
            <div className="kpi-label">Mention rate</div>
            <div className="kpi-value">{latest ? `${(latest.mention_rate * 100).toFixed(0)}%` : "—"}</div>
          </div>
          <div className="kpi">
            <div className="kpi-label">Share of voice</div>
            <div className="kpi-value">{latest ? `${(latest.share_of_voice * 100).toFixed(0)}%` : "—"}</div>
          </div>
          <div className="kpi">
            <div className="kpi-label">Citation rate</div>
            <div className="kpi-value">{latest ? `${(latest.citation_rate * 100).toFixed(0)}%` : "—"}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Visibility over time</h2>
        <VisibilityTrend scores={scoresQ.data ?? []} />
      </div>

      <div className="card">
        <h2>Recent runs</h2>
        {runsQ.data && runsQ.data.length === 0 && <p className="muted">No runs yet.</p>}
        {runsQ.data?.map((run) => (
          <div key={run.id} className="run">
            <div className="run-time">{new Date(run.run_at).toLocaleString()}</div>
            <p className="run-answer">{run.answer_text.slice(0, 240)}…</p>
            <div className="chips">
              {run.mentions.length === 0 && <span className="muted">No tracked brands mentioned</span>}
              {run.mentions.map((m) => (
                <span key={m.entity_name} className={m.is_tracked_brand ? "chip brand" : "chip"}>
                  {m.entity_name} · #{m.position}
                </span>
              ))}
            </div>
            <div className="cited">
              Cited: {[...new Set(run.citations.map((c) => c.domain))].join(", ") || "none"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
