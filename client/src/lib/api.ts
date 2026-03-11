const API_BASE = "/api";
const JWT_KEY = "aic_jwt";

function getAuthHeaders(): Record<string, string> {
  try {
    const jwt = localStorage.getItem(JWT_KEY);
    if (jwt) return { Authorization: `Bearer ${jwt}` };
  } catch {
    // localStorage unavailable
  }
  return {};
}

export async function startAnalysis(url: string): Promise<{ id: string; status: string }> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error("Failed to start analysis");
  return res.json();
}

export async function getResults(id: string, token?: string): Promise<AnalysisResponse> {
  const params = token ? `?token=${encodeURIComponent(token)}` : "";
  const res = await fetch(`${API_BASE}/results/${id}${params}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch results");
  return res.json();
}

export async function requestVerification(data: VerifyRequest): Promise<VerifyResponse> {
  const res = await fetch(`${API_BASE}/verify/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to send code" }));
    throw new Error(err.detail || "Failed to send code");
  }
  return res.json();
}

export async function confirmVerification(
  data: VerifyConfirm & { create_account?: boolean },
): Promise<VerifyConfirmResponse> {
  const res = await fetch(`${API_BASE}/verify/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to verify code");
  return res.json();
}

export async function googleAuth(data: GoogleAuthData): Promise<{ jwt: string }> {
  const res = await fetch(`${API_BASE}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Google sign-in failed" }));
    throw new Error(err.detail || "Google sign-in failed");
  }
  return res.json();
}

export interface GoogleAuthData {
  credential: string;
  dealership: string;
  phone: string;
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

// Admin API
export interface AdminStats {
  total_analyses: number;
  total_leads: number;
  total_accounts: number;
  avg_score: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminAnalysis {
  id: string;
  url: string;
  score: number | null;
  grade: string | null;
  status: string;
  error: string | null;
  created_at: string;
}

export interface AdminLead {
  id: number;
  name: string;
  email: string;
  dealership: string;
  phone: string;
  method: string;
  verified: boolean;
  created_account: boolean;
  created_at: string;
  analysis_url: string | null;
  analysis_score: number | null;
}

export interface AdminAccount {
  email: string;
  name: string;
  dealership: string;
  phone: string;
  provider: string;
  created_at: string;
}

async function adminFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...getAuthHeaders(), ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export function fetchAdminStats(): Promise<AdminStats> {
  return adminFetch("/admin/stats");
}

export function fetchAdminAnalyses(limit = 50, offset = 0): Promise<PaginatedResponse<AdminAnalysis>> {
  return adminFetch(`/admin/analyses?limit=${limit}&offset=${offset}`);
}

export function fetchAdminAnalysisDetail(id: string): Promise<any> {
  return adminFetch(`/admin/analyses/${id}`);
}

export function fetchAdminLeads(limit = 50, offset = 0): Promise<PaginatedResponse<AdminLead>> {
  return adminFetch(`/admin/leads?limit=${limit}&offset=${offset}`);
}

export function fetchAdminAccounts(limit = 50, offset = 0): Promise<PaginatedResponse<AdminAccount>> {
  return adminFetch(`/admin/accounts?limit=${limit}&offset=${offset}`);
}

export function deleteAdminAccount(email: string): Promise<{ success: boolean; message: string }> {
  return adminFetch(`/admin/accounts/${encodeURIComponent(email)}`, { method: "DELETE" });
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
  cloudflare_ip_whitelisted: boolean;
}

export interface AIProviderVerification {
  provider_name: string;
  could_access: boolean | null;
  returned_price: string;
  price_matches: boolean;
  returned_vin: string;
  vin_matches: boolean;
  response_text: string;
  error: string;
}

export interface AILiveVerifyResult {
  verified: boolean;
  providers: AIProviderVerification[];
  ground_truth_used: {
    vdp_url: string;
    expected_price: string;
    expected_vin: string;
    vehicle_title: string;
  } | null;
  details: string;
}

// ── V2 Types ──

export interface GroundTruthPage {
  url: string;
  page_type: string;
  accessible: boolean;
  price: string;
  vin: string;
  vehicle_title: string;
  vehicle_count: number;
  robots_rules: Record<string, string>;
  sitemap_url_count: number;
  raw_content: string;
}

export interface GroundTruthResult {
  pages: GroundTruthPage[];
  source: string;
  crawl_time: number;
  domain: string;
}

export interface AIVerifyCheck {
  check_type: string;
  could_access: boolean | null;
  data_returned: string;
  data_expected: string;
  match_score: number;
}

export interface AIProviderVerificationV2 {
  provider_name: string;
  checks: AIVerifyCheck[];
  overall_access: string;
  access_score: number;
  response_text: string;
  error: string;
}

export interface AILiveVerifyResultV2 {
  ground_truth: GroundTruthResult | null;
  providers: AIProviderVerificationV2[];
  summary: string;
  ai_verify_score: number;
}

export interface AnalysisResponse {
  id: string;
  url: string;
  status: string;
  gated: boolean;
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
  content_signal: any;
  rsl: any;
  faq_schema: any;
  ai_live_verify: AILiveVerifyResultV2 | AILiveVerifyResult | null;
  issues: Issue[];
  recommendations: string[];
  analysis_time: number | null;
}

export interface VerifyRequest {
  analysis_id: string;
  name: string;
  email: string;
  dealership: string;
  phone?: string;
  method: "email" | "sms";
}

export interface VerifyConfirm {
  analysis_id: string;
  code: string;
}

export interface VerifyResponse {
  success: boolean;
  message: string;
  method: string;
}

export interface VerifyConfirmResponse {
  success: boolean;
  token: string;
  jwt: string;
  message: string;
}

export interface AuthMeResponse {
  email: string;
  name: string;
  dealership: string;
  phone: string;
}
