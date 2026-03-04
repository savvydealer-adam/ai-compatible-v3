import { useEffect } from "react";
import { useRoute } from "wouter";
import { useAnalysis } from "../hooks/useAnalysis";
import ScoreCard from "../components/ScoreCard";
import GradeBreakdown from "../components/GradeBreakdown";
import BotStatusGrid from "../components/BotStatusGrid";
import IssuesList from "../components/IssuesList";
import LeadCaptureForm from "../components/LeadCaptureForm";
import ProgressOverlay from "../components/ProgressOverlay";
import { ExternalLink, Clock, Globe, Server } from "lucide-react";

export default function Results() {
  const [, params] = useRoute("/results/:id");
  const { data, isLoading, error, progress, pollResults } = useAnalysis();

  useEffect(() => {
    if (params?.id) {
      pollResults(params.id);
    }
  }, [params?.id, pollResults]);

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

  const { score, bot_permissions, issues, recommendations, provider, analysis_time, blocking, markdown_agents, llms_txt, faq_schema, sitemap, inventory, vdp } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
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
          {analysis_time && (
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" /> {analysis_time}s
            </span>
          )}
          {provider && provider.name !== "Unknown" && (
            <span className="flex items-center gap-1">
              <Server className="w-4 h-4" /> {provider.name}
            </span>
          )}
        </div>
      </div>

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
          value={blocking?.cloudflare_detected ? "Detected" : "Not detected"}
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Markdown for Agents"
          value={markdown_agents?.available ? "Supported" : "Not available"}
          good={markdown_agents?.available}
        />
        <StatCard
          label="llms.txt"
          value={llms_txt?.found ? "Found" : "Not found"}
          good={llms_txt?.found}
        />
        <StatCard
          label="FAQPage Schema"
          value={faq_schema?.found ? `${faq_schema.question_count} questions` : "Not found"}
          good={faq_schema?.found}
        />
        <StatCard
          label="Site Blocked"
          value={blocking?.is_blocked ? "Yes" : "No"}
          good={!blocking?.is_blocked}
        />
      </div>

      {/* Bot status grid */}
      <BotStatusGrid permissions={bot_permissions} />

      {/* Issues + Recommendations */}
      <IssuesList issues={issues} recommendations={recommendations} />

      {/* Lead capture */}
      <LeadCaptureForm
        analysisUrl={data.url}
        score={score?.total_score ?? null}
      />
    </div>
  );
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
