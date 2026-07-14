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
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const rows = promptsQ.data ?? [];

  const invalidate = () => {
    for (const k of ["prompts", "breakdown", "gaps", "intent"]) {
      qc.invalidateQueries({ queryKey: [k, brandId] });
    }
  };
  const clearSel = () => setSelected(new Set());

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
    mutationFn: (ids: string[]) => api.bulkDeletePrompts(brandId, ids, token),
    onSuccess: () => {
      invalidate();
      clearSel();
    },
  });
  const refineM = useMutation({
    mutationFn: (ids: string[]) => api.refinePrompts(brandId, ids, token),
    onSuccess: () => {
      invalidate();
      clearSel();
    },
  });

  const busy = delM.isPending || refineM.isPending || genM.isPending;
  const allChecked = rows.length > 0 && selected.size === rows.length;
  const selIds = [...selected];

  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  const toggleAll = () => setSelected(allChecked ? new Set() : new Set(rows.map((r) => r.id)));

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
            <span className="muted">{rows.length} active · edit, select, or generate more</span>
          </div>
          <button className="btn secondary" onClick={onClose}>
            Done
          </button>
        </div>

        {rows.length > 0 && (
          <div className="bulk-bar">
            <label className="bulk-all">
              <input type="checkbox" checked={allChecked} onChange={toggleAll} />
              Select all
            </label>
            {selected.size > 0 && (
              <div className="bulk-actions">
                <span className="muted">{selected.size} selected</span>
                <button
                  className="btn secondary"
                  disabled={busy}
                  onClick={() => refineM.mutate(selIds)}
                >
                  {refineM.isPending ? "Refining…" : "Refine"}
                </button>
                <button className="btn danger" disabled={busy} onClick={() => delM.mutate(selIds)}>
                  {delM.isPending ? "Deleting…" : "Delete"}
                </button>
              </div>
            )}
          </div>
        )}

        <div className="modal-body">
          {rows.length === 0 && !promptsQ.isLoading && (
            <p className="muted">No prompts yet. Generate a first batch below.</p>
          )}
          {rows.map((p) => (
            <div key={p.id} className={selected.has(p.id) ? "prompt-row sel" : "prompt-row"}>
              <input
                type="checkbox"
                checked={selected.has(p.id)}
                onChange={() => toggle(p.id)}
              />
              <input
                className="prompt-input"
                defaultValue={p.text}
                onChange={(e) => setDrafts((d) => ({ ...d, [p.id]: e.target.value }))}
                onBlur={() => commit(p)}
              />
              <span className="chip">{p.intent_type ? INTENT_LABEL[p.intent_type] ?? p.intent_type : "—"}</span>
            </div>
          ))}
        </div>

        <div className="modal-foot">
          <button className="btn" disabled={genM.isPending} onClick={() => genM.mutate()}>
            {genM.isPending ? "Generating…" : rows.length ? "Generate 10 more" : "Generate 10 prompts"}
          </button>
          {(genM.error || saveM.error || delM.error || refineM.error) && (
            <span className="err">
              {String(((genM.error || saveM.error || delM.error || refineM.error) as Error).message)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
