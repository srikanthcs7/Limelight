import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ENGINE_LABELS, type Brand } from "../api/client";

const FREQUENCIES = ["manual", "hourly", "daily", "weekly"];

export function SettingsPanel({ brand, token }: { brand: Brand; token: string }) {
  const qc = useQueryClient();
  const enginesQ = useQuery({ queryKey: ["engines"], queryFn: api.engines });

  const [engines, setEngines] = useState<string[]>(brand.tracked_engines);
  const [freq, setFreq] = useState(brand.run_frequency);
  const [location, setLocation] = useState(brand.location ?? "");
  const [language, setLanguage] = useState(brand.language);

  const saveM = useMutation({
    mutationFn: () =>
      api.updateSettings(
        brand.id,
        { tracked_engines: engines, run_frequency: freq, location: location || null, language },
        token,
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brands"] }),
  });

  const toggle = (key: string) =>
    setEngines((cur) => (cur.includes(key) ? cur.filter((e) => e !== key) : [...cur, key]));

  const available = enginesQ.data?.engines ?? ["openai"];

  return (
    <div className="settings-panel">
      <div className="field">
        <label>Engines tracked</label>
        <div className="engine-checks">
          {available.map((e) => (
            <label key={e} className={engines.includes(e) ? "engchk on" : "engchk"}>
              <input type="checkbox" checked={engines.includes(e)} onChange={() => toggle(e)} />
              {ENGINE_LABELS[e] ?? e}
            </label>
          ))}
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Run frequency</label>
          <select value={freq} onChange={(e) => setFreq(e.target.value)}>
            {FREQUENCIES.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Location (for Google AI Overviews)</label>
          <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="United States" />
        </div>
        <div className="field">
          <label>Language</label>
          <input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="en" style={{ width: 70 }} />
        </div>
      </div>

      <div className="toolbar">
        <button className="btn" disabled={!token || saveM.isPending || engines.length === 0} onClick={() => saveM.mutate()}>
          {saveM.isPending ? "Saving…" : "Save settings"}
        </button>
        {saveM.isSuccess && !saveM.isPending && <span className="ok">Saved.</span>}
        {saveM.error && <span className="err">{String((saveM.error as Error).message)}</span>}
      </div>
    </div>
  );
}
