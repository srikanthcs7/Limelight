import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ENGINE_LABELS } from "../api/client";
import { VisibilityTrend } from "../charts/VisibilityTrend";
import { SettingsPanel } from "../components/SettingsPanel";
import { CompetitorTable } from "../components/CompetitorTable";
import { SourcesBar } from "../components/SourcesBar";
import { PromptDrilldown } from "../components/PromptDrilldown";
import { GapList } from "../components/GapList";
import { CoverageRing } from "../components/CoverageRing";
import { PromptsModal } from "../components/PromptsModal";
import { IntentCoverage } from "../components/IntentCoverage";
import { ShareTrend } from "../charts/ShareTrend";

export function Dashboard() {
  const qc = useQueryClient();
  const brandsQ = useQuery({ queryKey: ["brands"], queryFn: api.brands });
  const [brandId, setBrandId] = useState<string | null>(null);
  const [token, setToken] = useState<string>(
    () => localStorage.getItem("limelight_admin_token") ?? "",
  );
  const [showSettings, setShowSettings] = useState(false);
  const [showPrompts, setShowPrompts] = useState(false);
  const [win, setWin] = useState<"7d" | "30d" | "all">("7d");
  const [engine, setEngine] = useState<string | null>(null);

  const activeBrandId = brandId ?? brandsQ.data?.[0]?.id ?? null;
  const brand = brandsQ.data?.find((b) => b.id === activeBrandId);
  const engines = brand?.tracked_engines ?? ["openai"];
  const eng = engine && engines.includes(engine) ? engine : engines[0] ?? "openai";

  const scoresQ = useQuery({
    queryKey: ["scores", activeBrandId, eng],
    queryFn: () => api.scores(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const runsQ = useQuery({
    queryKey: ["runs", activeBrandId, eng],
    queryFn: () => api.runs(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const promptsQ = useQuery({
    queryKey: ["prompts", activeBrandId],
    queryFn: () => api.prompts(activeBrandId!),
    enabled: !!activeBrandId,
  });
  const sovQ = useQuery({
    queryKey: ["sov", activeBrandId, eng],
    queryFn: () => api.shareOfVoice(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const sourcesQ = useQuery({
    queryKey: ["sources", activeBrandId, eng],
    queryFn: () => api.sources(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const breakdownQ = useQuery({
    queryKey: ["breakdown", activeBrandId, eng],
    queryFn: () => api.promptBreakdown(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const gapsQ = useQuery({
    queryKey: ["gaps", activeBrandId, eng],
    queryFn: () => api.gaps(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const intentQ = useQuery({
    queryKey: ["intent", activeBrandId, eng],
    queryFn: () => api.intentCoverage(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const timelineQ = useQuery({
    queryKey: ["timeline", activeBrandId, eng],
    queryFn: () => api.sovTimeline(activeBrandId!, eng),
    enabled: !!activeBrandId,
  });
  const recommendM = useMutation({ mutationFn: () => api.recommend(activeBrandId!, eng, token) });

  const saveToken = (v: string) => {
    setToken(v);
    localStorage.setItem("limelight_admin_token", v);
  };

  const refresh = () => {
    for (const k of ["runs", "scores", "prompts", "sov", "sources", "breakdown", "gaps", "intent", "timeline"]) {
      qc.invalidateQueries({ queryKey: [k, activeBrandId] });
    }
  };

  const seedM = useMutation({
    mutationFn: () => api.seed(token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brands"] }),
  });
  const runM = useMutation({ mutationFn: () => api.triggerRun(activeBrandId!, token), onSuccess: refresh });

  const windowScores = (scoresQ.data ?? [])
    .filter((s) => s.window_label === win)
    .sort((a, b) => a.window_end.localeCompare(b.window_end));
  const latest = windowScores[windowScores.length - 1];
  const noBrands = brandsQ.data && brandsQ.data.length === 0;
  const busy = seedM.isPending || runM.isPending;
  const error = seedM.error ?? runM.error;
  const activePrompts = promptsQ.data?.filter((p) => p.active).length ?? 0;
  const breakdown = breakdownQ.data ?? [];
  const mentionedCount = breakdown.filter((r) => r.brand_mentioned).length;

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
          <span className="pill">🥇 {brand.competitors.length} competitors</span>
          <span className="pill">⏱ {brand.run_frequency}</span>
        </div>
      )}

      {brand && (
        <div className="engine-tabs">
          {engines.map((e) => (
            <button
              key={e}
              className={eng === e ? "etab active" : "etab"}
              onClick={() => setEngine(e)}
            >
              {ENGINE_LABELS[e] ?? e}
            </button>
          ))}
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
                  disabled={!token}
                  onClick={() => setShowPrompts(true)}
                >
                  Manage prompts
                </button>
              </>
            )}
            {error && <span className="err">{String((error as Error).message ?? error)}</span>}
            {runM.isSuccess && !busy && <span className="ok">Ran {runM.data.runs} prompt(s).</span>}
          </div>
          {brand && token && <SettingsPanel brand={brand} token={token} />}
        </div>
      )}

      {showPrompts && activeBrandId && (
        <PromptsModal brandId={activeBrandId} token={token} onClose={() => setShowPrompts(false)} />
      )}

      <div className="card">
        <div className="card-head">
          <h2>Visibility score</h2>
          <div className="segmented">
            {(["7d", "30d", "all"] as const).map((w) => (
              <button
                key={w}
                className={win === w ? "seg active" : "seg"}
                onClick={() => setWin(w)}
              >
                {w === "all" ? "All" : w}
              </button>
            ))}
          </div>
        </div>
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
        <h2>Visibility over time · {win === "all" ? "all-time" : win}</h2>
        <VisibilityTrend scores={windowScores} />
      </div>

      <div className="card">
        <h2>Share of voice over time</h2>
        <ShareTrend timeline={timelineQ.data ?? { days: [], series: [] }} />
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Share of voice</h2>
          <div className="scroll-box">
            <CompetitorTable rows={sovQ.data ?? []} />
          </div>
        </div>
        <div className="card">
          <h2>Top cited sources</h2>
          <div className="scroll-box">
            <SourcesBar rows={sourcesQ.data ?? []} />
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Coverage by intent</h2>
        <IntentCoverage rows={intentQ.data ?? []} />
      </div>

      <div className="card">
        <h2>Gaps &amp; recommendations</h2>
        <GapList
          gaps={gapsQ.data?.prompt_gaps ?? []}
          recommendations={recommendM.data?.recommendations ?? null}
          onRecommend={() => recommendM.mutate()}
          canRecommend={!!token && !busy}
          loading={recommendM.isPending}
        />
        {recommendM.error && (
          <div className="err" style={{ marginTop: 8 }}>
            {String((recommendM.error as Error).message)}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Prompt breakdown</h2>
          {breakdown.length > 0 && <CoverageRing mentioned={mentionedCount} total={breakdown.length} />}
        </div>
        <div className="scroll-box tall">
          <PromptDrilldown rows={breakdown} />
        </div>
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
                  {m.sentiment && <i className={`sdot ${m.sentiment}`} />}
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
