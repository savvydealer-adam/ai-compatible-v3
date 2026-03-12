import { useEffect, useState } from "react";
import { useRoute } from "wouter";
import { useAnalysis } from "../hooks/useAnalysis";
import { useAuth } from "../hooks/useAuth";
import { useVerification } from "../hooks/useVerification";
import ScoreCard from "../components/ScoreCard";
import GradeBreakdown from "../components/GradeBreakdown";
import BotStatusGrid from "../components/BotStatusGrid";
import IssuesList from "../components/IssuesList";
import LiveVerifyCard from "../components/LiveVerifyCard";
import VerificationForm from "../components/VerificationForm";
import ProgressOverlay from "../components/ProgressOverlay";
import { ExternalLink, Clock, Server } from "lucide-react";

export default function Results() {
  const [, params] = useRoute("/results/:id");
  const analysisId = params?.id || "";
  const auth = useAuth();
  const { data, isLoading, error, progress, pollResults, refetch } = useAnalysis();
  const verification = useVerification(analysisId, { onAccountCreated: auth.login });
  const [accountMode, setAccountMode] = useState(false);

  // Start polling with token if we have one
  useEffect(() => {
    if (analysisId) {
      pollResults(analysisId, verification.token || undefined);
    }
  }, [analysisId, pollResults, verification.token]);

  // Re-fetch with token when verification completes
  useEffect(() => {
    if (verification.isVerified && verification.token && analysisId) {
      refetch(analysisId, verification.token);
    }
  }, [verification.isVerified, verification.token, analysisId, refetch]);

  // Re-fetch when user is logged in (JWT auto-unlocks)
  useEffect(() => {
    if (auth.isLoggedIn && analysisId && data?.gated) {
      refetch(analysisId, "");
    }
  }, [auth.isLoggedIn, analysisId, data?.gated, refetch]);

  if (error) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-bold text-destructive mb-2">Analysis Error</h2>
        <p className="text-muted-foreground">{error}</p>
        <a href="/" className="text-primary mt-4 inline-block">Try again</a>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="max-w-3xl mx-auto">
        <h2 className="text-xl font-semibold mb-4">Analyzing...</h2>
        {progress && <ProgressOverlay progress={progress} />}
        <p className="text-sm text-muted-foreground">
          This usually takes 30-60 seconds. We're testing AI bot access,
          parsing schemas, and checking discoverability.
        </p>
      </div>
    );
  }

  if (data.status === "error") {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-bold text-destructive mb-2">Analysis Failed</h2>
        <p className="text-muted-foreground">{data.error}</p>
        <a href="/" className="text-primary mt-4 inline-block">Try again</a>
      </div>
    );
  }

  const isGated = data.status === "complete" && data.gated;

  // Gated view — score only + verification form (skip if logged in)
  if (isGated && !verification.isVerified && !auth.isLoggedIn) {
    return (
      <div className="space-y-6">
        <ResultsHeader data={data} />

        {data.score && (
          <div className="max-w-sm mx-auto">
            <ScoreCard score={data.score} />
          </div>
        )}

        <VerificationForm
          analysisId={analysisId}
          step={verification.step as "info" | "code"}
          formData={verification.formData}
          setFormData={verification.setFormData}
          isSubmitting={verification.isSubmitting}
          error={verification.error}
          onRequestCode={verification.requestCode}
          onConfirmCode={verification.confirmCode}
          onEditInfo={verification.editInfo}
          accountMode={accountMode}
          onSetAccountMode={setAccountMode}
          onGoogleAuth={auth.login}
        />
      </div>
    );
  }

  // Full view — all results
  const { score, bot_permissions, issues, recommendations, provider, analysis_time, blocking, markdown_agents, faq_schema, sitemap, inventory, vdp, ai_live_verify } = data;

  return (
    <div className="space-y-6">
      <ResultsHeader data={data} />

      {/* Score + Breakdown */}
      {score && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <ScoreCard score={score} />
          <div className="md:col-span-2">
            <GradeBreakdown categories={score.categories} />
          </div>
        </div>
      )}

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="CloudFlare"
          value={blocking?.cloudflare_detected ? cfTierLabel(blocking.cloudflare_blocking_tier) : "Not detected"}
          good={!blocking?.cloudflare_detected}
        />
        <StatCard
          label="Sitemap"
          value={sitemap?.found ? "Found" : "Not found"}
          good={sitemap?.found}
        />
        <StatCard
          label="Inventory"
          value={inventory?.found ? `Found (${inventory?.vehicle_count || 0} vehicles)` : "Not found"}
          good={inventory?.found}
        />
        <StatCard
          label="VDP Schema"
          value={vdp?.found ? "Found" : "Not found"}
          good={vdp?.found}
        />
      </div>

      {/* v3 features */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Markdown for Agents"
          value={markdown_agents?.available ? "Supported" : "Not available"}
          good={markdown_agents?.available}
        />
        <StatCard
          label="FAQPage Schema"
          value={faq_schema?.found ? `${faq_schema.question_count} questions` : "Not found"}
          good={faq_schema?.found}
        />
        <StatCard
          label="Site Blocked"
          value={blockingLabel(blocking)}
          good={!blocking?.is_blocked ? true : blocking?.blocking_type === "datacenter_ip" ? undefined : false}
        />
      </div>

      {/* Bot status grid */}
      <BotStatusGrid permissions={bot_permissions} />

      {/* Live AI Verification */}
      {ai_live_verify && <LiveVerifyCard data={ai_live_verify} />}

      {/* Issues + Recommendations */}
      <IssuesList issues={issues} recommendations={recommendations} />
    </div>
  );
}

function ResultsHeader({ data }: { data: { url: string; analysis_time?: number | null; provider?: any } }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold">Analysis Results</h1>
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary flex items-center gap-1 mt-1"
        >
          {data.url} <ExternalLink className="w-3 h-3" />
        </a>
      </div>
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        {data.analysis_time && (
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" /> {data.analysis_time}s
          </span>
        )}
        {data.provider && data.provider.name !== "Unknown" && (
          <span className="flex items-center gap-1">
            <Server className="w-4 h-4" /> {data.provider.name}
          </span>
        )}
      </div>
    </div>
  );
}

const CF_TIER_LABELS: Record<string, string> = {
  none: "Not detected",
  passive: "Present (not blocking)",
  ai_scrapers_toggle: "AI Scrapers Toggle",
  bot_fight_mode: "Bot Fight Mode",
  super_bot_fight_mode: "Super Bot Fight Mode",
  enterprise: "Enterprise Bot Mgmt",
};

function cfTierLabel(tier?: string): string {
  if (!tier || tier === "none") return "Detected";
  return CF_TIER_LABELS[tier] || "Detected";
}

function blockingLabel(blocking: any): string {
  if (!blocking?.is_blocked) return "No";
  if (blocking.blocking_type === "datacenter_ip") return "DC IP Only (AI OK)";
  if (blocking.blocking_type === "ai_block") return "Yes (AI Blocked)";
  return "Yes";
}

function StatCard({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className={`text-sm font-medium ${good ? "text-green-600" : good === false ? "text-red-600" : ""}`}>
        {value}
      </div>
    </div>
  );
}
