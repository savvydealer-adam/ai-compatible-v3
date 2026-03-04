const API_BASE = "/api";

export async function startAnalysis(url: string): Promise<{ id: string; status: string }> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error("Failed to start analysis");
  return res.json();
}

export async function getResults(id: string): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/results/${id}`);
  if (!res.ok) throw new Error("Failed to fetch results");
  return res.json();
}

export async function submitLead(data: LeadData): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/leads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to submit lead");
  return res.json();
}

// Types
export interface LeadData {
  name: string;
  email: string;
  dealership: string;
  phone?: string;
  analysis_url?: string;
  score?: number;
}

export interface CategoryScore {
  name: string;
  score: number;
  max_score: number;
  details: string[];
}

export interface ScoreResponse {
  total_score: number;
  max_score: number;
  grade: string;
  grade_label: string;
  categories: CategoryScore[];
  bonus_points: number;
}

export interface Issue {
  severity: string;
  category: string;
  message: string;
  recommendation: string;
}

export interface BotPermission {
  bot_name: string;
  user_agent: string;
  robots_status: string;
  http_status: number | null;
  http_accessible: boolean | null;
  response_time: number | null;
  details: string;
}

export interface AnalysisResponse {
  id: string;
  url: string;
  status: string;
  progress: { step: string; percent: number } | null;
  error: string | null;
  score: ScoreResponse | null;
  blocking: any;
  bot_permissions: BotPermission[];
  bot_protection: any;
  inventory: any;
  vdp: any;
  sitemap: any;
  meta_tags: any;
  provider: any;
  markdown_agents: any;
  llms_txt: any;
  content_signal: any;
  rsl: any;
  faq_schema: any;
  issues: Issue[];
  recommendations: string[];
  analysis_time: number | null;
}
