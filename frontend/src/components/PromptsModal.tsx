import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Prompt } from "../api/client";

const INTENT_LABEL: Record<string, string> = {
  best_of: "Best-of",
  comparison: "Comparison",
  alternatives: "Alternatives",
  problem_first: "Problem",
};

export function PromptsModal({
  brandId,
  token,
  onClose,
}: {
  brandId: string;
  token: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const promptsQ = useQuery({
    queryKey: ["prompts", brandId],
    queryFn: () => api.prompts(brandId, true),
  });
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const invalidate = () => {
    for (const k of ["prompts", "breakdown", "gaps"]) {
      qc.invalidateQueries({ queryKey: [k, brandId] });
    }
  };

  const genM = useMutation({
    mutationFn: () => api.generatePrompts(brandId, token, 10),
    onSuccess: invalidate,
  });
  const saveM = useMutation({
    mutationFn: (p: { id: string; text: string }) =>
      api.updatePrompt(brandId, p.id, { text: p.text }, token),
    onSuccess: invalidate,
  });
  const delM = useMutation({
    mutationFn: (id: string) => api.deletePrompt(brandId, id, token),
    onSuccess: invalidate,
  });

  const rows = promptsQ.data ?? [];

  const commit = (p: Prompt) => {
    const draft = drafts[p.id];
    if (draft !== undefined && draft.trim() && draft !== p.text) {
      saveM.mutate({ id: p.id, text: draft.trim() });
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h2 style={{ margin: 0 }}>Tracked prompts</h2>
            <span className="muted">{rows.length} active · edit or remove, then generate more</span>
          </div>
          <button className="btn secondary" onClick={onClose}>
            Done
          </button>
        </div>

        <div className="modal-body">
          {rows.length === 0 && !promptsQ.isLoading && (
            <p className="muted">No prompts yet. Generate a first batch below.</p>
          )}
          {rows.map((p) => (
            <div key={p.id} className="prompt-row">
              <input
                className="prompt-input"
                defaultValue={p.text}
                onChange={(e) => setDrafts((d) => ({ ...d, [p.id]: e.target.value }))}
                onBlur={() => commit(p)}
              />
              <span className="chip">{p.intent_type ? INTENT_LABEL[p.intent_type] ?? p.intent_type : "—"}</span>
              <button
                className="icon-btn"
                title="Remove"
                disabled={delM.isPending}
                onClick={() => delM.mutate(p.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        <div className="modal-foot">
          <button className="btn" disabled={genM.isPending} onClick={() => genM.mutate()}>
            {genM.isPending ? "Generating…" : rows.length ? "Generate 10 more" : "Generate 10 prompts"}
          </button>
          {genM.isSuccess && !genM.isPending && (
            <span className="ok">Added {genM.data.added_prompts}.</span>
          )}
          {(genM.error || saveM.error || delM.error) && (
            <span className="err">
              {String(((genM.error || saveM.error || delM.error) as Error).message)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
