import type { PromptRow } from "../api/client";

export function GapList({
  gaps,
  recommendations,
  onRecommend,
  canRecommend,
  loading,
}: {
  gaps: PromptRow[];
  recommendations: string[] | null;
  onRecommend: () => void;
  canRecommend: boolean;
  loading: boolean;
}) {
  return (
    <div>
      <div className="gap-head">
        <span className="muted">
          {gaps.length === 0
            ? "No gaps yet — you're mentioned everywhere we've run, or no runs yet."
            : `${gaps.length} prompt${gaps.length > 1 ? "s" : ""} where competitors appear and you don't.`}
        </span>
        <button className="btn secondary" disabled={!canRecommend || loading} onClick={onRecommend}>
          {loading ? "Thinking…" : "Generate recommendations"}
        </button>
      </div>

      {gaps.length > 0 && (
        <ul className="gap-ul">
          {gaps.map((g) => (
            <li key={g.prompt_id}>
              <span>{g.text}</span>
              <span className="muted"> — {g.competitors_present.slice(0, 3).join(", ")}</span>
            </li>
          ))}
        </ul>
      )}

      {recommendations && recommendations.length > 0 && (
        <div className="recs">
          <div className="recs-title">Recommended actions</div>
          <ol className="recs-ol">
            {recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
