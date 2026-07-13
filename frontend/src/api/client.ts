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
  competitors: Competitor[];
}

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

async function post<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "X-Admin-Token": token },
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

export const api = {
  brands: () => get<Brand[]>("/brands"),
  runs: (brandId: string) => get<Run[]>(`/brands/${brandId}/runs`),
  scores: (brandId: string) => get<Score[]>(`/brands/${brandId}/scores`),
  seed: (token: string) => post<{ brand_id: string; display_name: string }>("/admin/seed", token),
  triggerRun: (brandId: string, token: string) =>
    post<{ runs: number }>(`/brands/${brandId}/runs`, token),
};
