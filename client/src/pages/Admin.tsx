import { useState, useEffect, useCallback } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { GoogleLogin, type CredentialResponse } from "@react-oauth/google";
import { ShieldAlert, BarChart3, Users, UserCheck, Trash2 } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import {
  googleAuth,
  fetchAdminStats,
  fetchAdminAnalyses,
  fetchAdminLeads,
  fetchAdminAccounts,
  deleteAdminAccount,
  type AdminStats,
  type AdminAnalysis,
  type AdminLead,
  type AdminAccount,
  type PaginatedResponse,
} from "../lib/api";

const PAGE_SIZE = 25;

function StatCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: any }) {
  return (
    <div className="bg-white border rounded-lg p-4 flex items-center gap-3">
      <div className="p-2 rounded-md bg-primary/10 text-primary">
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

function Pagination({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}) {
  const pages = Math.ceil(total / limit);
  const current = Math.floor(offset / limit) + 1;
  if (pages <= 1) return null;

  return (
    <div className="flex items-center gap-2 mt-4 justify-end text-sm">
      <button
        disabled={current <= 1}
        onClick={() => onChange(offset - limit)}
        className="px-3 py-1 border rounded disabled:opacity-40"
      >
        Prev
      </button>
      <span className="text-muted-foreground">
        Page {current} of {pages}
      </span>
      <button
        disabled={current >= pages}
        onClick={() => onChange(offset + limit)}
        className="px-3 py-1 border rounded disabled:opacity-40"
      >
        Next
      </button>
    </div>
  );
}

function AnalysesTab() {
  const [data, setData] = useState<PaginatedResponse<AdminAnalysis> | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (off: number) => {
    setLoading(true);
    try {
      setData(await fetchAdminAnalyses(PAGE_SIZE, off));
    } catch {
      // handled by auth gate
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(offset); }, [offset, load]);

  if (loading) return <p className="py-4 text-muted-foreground">Loading...</p>;
  if (!data || data.items.length === 0) return <p className="py-4 text-muted-foreground">No analyses yet.</p>;

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4">ID</th>
              <th className="py-2 pr-4">URL</th>
              <th className="py-2 pr-4">Score</th>
              <th className="py-2 pr-4">Grade</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2">Date</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((a) => (
              <tr key={a.id} className="border-b hover:bg-muted/50">
                <td className="py-2 pr-4">
                  <a href={`/results/${a.id}`} className="text-primary hover:underline font-mono text-xs">
                    {a.id}
                  </a>
                </td>
                <td className="py-2 pr-4 max-w-[300px] truncate">{a.url}</td>
                <td className="py-2 pr-4 font-mono">{a.score ?? "-"}</td>
                <td className="py-2 pr-4 font-bold">{a.grade ?? "-"}</td>
                <td className="py-2 pr-4">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    a.status === "complete" ? "bg-green-100 text-green-700" :
                    a.status === "error" ? "bg-red-100 text-red-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>
                    {a.status}
                  </span>
                </td>
                <td className="py-2 text-muted-foreground">{new Date(a.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination total={data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
    </>
  );
}

function LeadsTab() {
  const [data, setData] = useState<PaginatedResponse<AdminLead> | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (off: number) => {
    setLoading(true);
    try {
      setData(await fetchAdminLeads(PAGE_SIZE, off));
    } catch {
      // handled by auth gate
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(offset); }, [offset, load]);

  if (loading) return <p className="py-4 text-muted-foreground">Loading...</p>;
  if (!data || data.items.length === 0) return <p className="py-4 text-muted-foreground">No leads yet.</p>;

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">Email</th>
              <th className="py-2 pr-4">Dealership</th>
              <th className="py-2 pr-4">Method</th>
              <th className="py-2 pr-4">Analysis</th>
              <th className="py-2">Date</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((l) => (
              <tr key={l.id} className="border-b hover:bg-muted/50">
                <td className="py-2 pr-4">{l.name}</td>
                <td className="py-2 pr-4">{l.email}</td>
                <td className="py-2 pr-4 max-w-[200px] truncate">{l.dealership}</td>
                <td className="py-2 pr-4">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{l.method}</span>
                </td>
                <td className="py-2 pr-4 text-muted-foreground truncate max-w-[200px]">
                  {l.analysis_url ? (
                    <span>{l.analysis_url} ({l.analysis_score ?? "-"})</span>
                  ) : "-"}
                </td>
                <td className="py-2 text-muted-foreground">{new Date(l.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination total={data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
    </>
  );
}

function AccountsTab() {
  const [data, setData] = useState<PaginatedResponse<AdminAccount> | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async (off: number) => {
    setLoading(true);
    try {
      setData(await fetchAdminAccounts(PAGE_SIZE, off));
    } catch {
      // handled by auth gate
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(offset); }, [offset, load]);

  const handleDelete = async (email: string) => {
    if (!confirm(`Delete account ${email}? This cannot be undone.`)) return;
    setDeleting(email);
    try {
      await deleteAdminAccount(email);
      load(offset);
    } catch {
      alert("Failed to delete account");
    }
    setDeleting(null);
  };

  if (loading) return <p className="py-4 text-muted-foreground">Loading...</p>;
  if (!data || data.items.length === 0) return <p className="py-4 text-muted-foreground">No accounts yet.</p>;

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4">Email</th>
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">Dealership</th>
              <th className="py-2 pr-4">Provider</th>
              <th className="py-2 pr-4">Date</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((a) => (
              <tr key={a.email} className="border-b hover:bg-muted/50">
                <td className="py-2 pr-4">{a.email}</td>
                <td className="py-2 pr-4">{a.name}</td>
                <td className="py-2 pr-4 max-w-[200px] truncate">{a.dealership}</td>
                <td className="py-2 pr-4">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">{a.provider}</span>
                </td>
                <td className="py-2 pr-4 text-muted-foreground">{new Date(a.created_at).toLocaleDateString()}</td>
                <td className="py-2">
                  <button
                    onClick={() => handleDelete(a.email)}
                    disabled={deleting === a.email}
                    className="text-red-500 hover:text-red-700 disabled:opacity-40"
                    title="Delete account"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination total={data.total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />
    </>
  );
}

const tabTriggerClass =
  "px-4 py-2 text-sm font-medium text-muted-foreground data-[state=active]:text-foreground data-[state=active]:border-b-2 data-[state=active]:border-primary";

export default function Admin() {
  const { user, isLoggedIn, login } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  const isAdmin = isLoggedIn && user?.email.endsWith("@savvydealer.com");

  useEffect(() => {
    if (isAdmin) {
      fetchAdminStats().then(setStats).catch(() => {});
    }
  }, [isAdmin]);

  const handleGoogleSuccess = async (response: CredentialResponse) => {
    if (!response.credential) return;
    setAuthError(null);
    try {
      const res = await googleAuth({
        credential: response.credential,
        dealership: "",
        phone: "",
      });
      if (res.jwt) {
        login(res.jwt);
      }
    } catch {
      setAuthError("Sign-in failed. Make sure you use a @savvydealer.com account.");
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="text-center py-20">
        <ShieldAlert className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
        <h1 className="text-2xl font-bold mb-2">Admin Sign In</h1>
        <p className="text-muted-foreground mb-6">Sign in with your @savvydealer.com Google account.</p>
        <div className="flex justify-center">
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setAuthError("Google sign-in was cancelled or failed")}
            size="large"
            theme="outline"
            text="signin_with"
          />
        </div>
        {authError && (
          <p className="text-red-500 text-sm mt-4">{authError}</p>
        )}
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-20">
        <ShieldAlert className="w-12 h-12 mx-auto text-red-400 mb-4" />
        <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
        <p className="text-muted-foreground">Admin access is restricted to @savvydealer.com accounts.</p>
        <a href="/" className="text-primary mt-4 inline-block hover:underline">Go home</a>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Analyses" value={stats?.total_analyses ?? "-"} icon={BarChart3} />
        <StatCard label="Leads" value={stats?.total_leads ?? "-"} icon={Users} />
        <StatCard label="Accounts" value={stats?.total_accounts ?? "-"} icon={UserCheck} />
        <StatCard label="Avg Score" value={stats?.avg_score ?? "-"} icon={BarChart3} />
      </div>

      {/* Tabs */}
      <Tabs.Root defaultValue="analyses">
        <Tabs.List className="flex border-b mb-4">
          <Tabs.Trigger value="analyses" className={tabTriggerClass}>Analyses</Tabs.Trigger>
          <Tabs.Trigger value="leads" className={tabTriggerClass}>Leads</Tabs.Trigger>
          <Tabs.Trigger value="accounts" className={tabTriggerClass}>Accounts</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="analyses"><AnalysesTab /></Tabs.Content>
        <Tabs.Content value="leads"><LeadsTab /></Tabs.Content>
        <Tabs.Content value="accounts"><AccountsTab /></Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
