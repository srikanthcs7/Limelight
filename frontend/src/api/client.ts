const BASE = import.meta.env.VITE_API_BASE ?? "";

export interface Competitor {
  id: string;
  name: string;
  aliases: string[];
  domain: string | null;
}

export interface Brand {
  id: string;
  domain: string;
  display_name: string;
  aliases: string[];
  category: string | null;
  created_at: string;
  tracked_engines: string[];
  run_frequency: string;
  location: string | null;
  language: string;
  last_run_at: string | null;
  competitors: Competitor[];
}

export interface BrandSettings {
  tracked_engines?: string[];
  run_frequency?: string;
  location?: string | null;
  language?: string;
}

export const ENGINE_LABELS: Record<string, string> = {
  openai: "ChatGPT",
  google_aio: "Google AI Overviews",
  gemini: "Gemini",
};

export interface Mention {
  entity_type: string;
  entity_name: string;
  is_tracked_brand: boolean;
  position: number | null;
  prominence: number | null;
  sentiment: string | null;
}

export interface Citation {
  url: string;
  domain: string;
  source_type: string | null;
}

export interface Run {
  id: string;
  prompt_id: string;
  engine_id: number;
  run_at: string;
  answer_text: string;
  mentions: Mention[];
  citations: Citation[];
}

export interface Score {
  window_label: string; // 'all' | '7d' | '30d'
  window_start: string;
  window_end: string;
  visibility_score: number;
  share_of_voice: number;
  mention_rate: number;
  citation_rate: number;
  computed_at: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function send<T>(method: string, path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "X-Admin-Token": token,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, token: string) => send<T>("POST", path, token);

export interface Prompt {
  id: string;
  text: string;
  intent_type: string | null;
  active: boolean;
  created_at: string;
}

export interface ShareRow {
  entity_name: string;
  is_tracked_brand: boolean;
  mentions: number;
  share: number;
  positive: number;
  neutral: number;
  negative: number;
}

export interface IntentRow {
  intent_type: string;
  total: number;
  mentioned: number;
  coverage: number;
}

export interface SovTimeline {
  days: string[];
  series: { name: string; is_tracked_brand: boolean; points: number[] }[];
}

export interface SourceRow {
  domain: string;
  citations: number;
}

export interface PromptRow {
  prompt_id: string;
  text: string;
  intent_type: string | null;
  runs_count: number;
  last_run_at: string | null;
  brand_mentioned: boolean;
  position: number | null;
  competitors_present: string[];
}

export const api = {
  brands: () => get<Brand[]>("/brands"),
  engines: () => get<{ engines: string[] }>("/brands/meta/engines"),
  updateSettings: (brandId: string, body: BrandSettings, token: string) =>
    send<Brand>("PATCH", `/brands/${brandId}/settings`, token, body),
  runs: (brandId: string, engine: string) => get<Run[]>(`/brands/${brandId}/runs?engine=${engine}`),
  scores: (brandId: string, engine: string) => get<Score[]>(`/brands/${brandId}/scores?engine=${engine}`),
  prompts: (brandId: string, activeOnly = false) =>
    get<Prompt[]>(`/brands/${brandId}/prompts${activeOnly ? "?active_only=true" : ""}`),
  updatePrompt: (brandId: string, promptId: string, body: { text?: string; active?: boolean }, token: string) =>
    send<Prompt>("PATCH", `/brands/${brandId}/prompts/${promptId}`, token, body),
  deletePrompt: (brandId: string, promptId: string, token: string) =>
    send<{ deleted: boolean }>("DELETE", `/brands/${brandId}/prompts/${promptId}`, token),
  seed: (token: string) => post<{ brand_id: string; display_name: string }>("/admin/seed", token),
  triggerRun: (brandId: string, token: string) =>
    post<{ runs: number }>(`/brands/${brandId}/runs`, token),
  generatePrompts: (brandId: string, token: string, target = 10) =>
    post<{ added_prompts: number }>(`/brands/${brandId}/prompts:generate?target=${target}`, token),
  shareOfVoice: (brandId: string, engine: string) =>
    get<ShareRow[]>(`/brands/${brandId}/share-of-voice?engine=${engine}`),
  sovTimeline: (brandId: string, engine: string) =>
    get<SovTimeline>(`/brands/${brandId}/share-of-voice/timeline?engine=${engine}`),
  intentCoverage: (brandId: string, engine: string) =>
    get<IntentRow[]>(`/brands/${brandId}/intent-coverage?engine=${engine}`),
  sources: (brandId: string, engine: string) =>
    get<SourceRow[]>(`/brands/${brandId}/sources?engine=${engine}`),
  promptBreakdown: (brandId: string, engine: string) =>
    get<PromptRow[]>(`/brands/${brandId}/prompt-breakdown?engine=${engine}`),
  gaps: (brandId: string, engine: string) =>
    get<{ prompt_gaps: PromptRow[]; source_gaps: SourceRow[] }>(`/brands/${brandId}/gaps?engine=${engine}`),
  recommend: (brandId: string, engine: string, token: string) =>
    post<{ recommendations: string[] }>(`/brands/${brandId}/gaps/recommend?engine=${engine}`, token),
};
