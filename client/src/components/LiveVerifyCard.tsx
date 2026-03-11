import { useState } from "react";
import type {
  AILiveVerifyResult,
  AILiveVerifyResultV2,
  AIProviderVerificationV2,
  AIVerifyCheck,
  GroundTruthPage,
} from "../lib/api";
import { Check, X, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";

type LiveVerifyData = AILiveVerifyResultV2 | AILiveVerifyResult;

interface LiveVerifyCardProps {
  data: LiveVerifyData;
}

function isV2(data: LiveVerifyData): data is AILiveVerifyResultV2 {
  return "ground_truth" in data;
}

export default function LiveVerifyCard({ data }: LiveVerifyCardProps) {
  if (!data) return null;

  if (isV2(data)) {
    return <LiveVerifyCardV2 data={data} />;
  }

  return <LiveVerifyCardV1 data={data} />;
}

// ── V2 Card: Comparison Table ──

function LiveVerifyCardV2({ data }: { data: AILiveVerifyResultV2 }) {
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);

  if (data.providers.length === 0) return null;

  const gt = data.ground_truth;
  const gtPages: Record<string, GroundTruthPage | undefined> = {};
  if (gt) {
    for (const page of gt.pages) {
      gtPages[page.page_type] = page;
    }
  }

  const checkTypes = ["robots", "inventory", "vdp_price", "vdp_vin", "sitemap"];
  const checkLabels: Record<string, string> = {
    robots: "robots.txt",
    inventory: "Inventory",
    vdp_price: "VDP Price",
    vdp_vin: "VDP VIN",
    sitemap: "Sitemap",
  };

  const providerLabels: Record<string, string> = {
    openai: "ChatGPT",
    gemini: "Gemini",
    kimi: "Kimi",
  };

  // Count accessible providers
  const accessibleCount = data.providers.filter(
    (p) => p.overall_access === "full" || p.overall_access === "partial"
  ).length;
  const totalCount = data.providers.filter((p) => p.overall_access !== "error").length;

  return (
    <div className="p-6 rounded-lg border bg-card">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-lg font-semibold">Live AI Verification</h2>
        <span className="text-sm font-medium text-muted-foreground">
          +{Math.round(data.ai_verify_score)}/10 pts
        </span>
      </div>

      {/* Summary bar */}
      <div
        className={`mb-4 px-3 py-2 rounded-md text-sm font-medium ${
          accessibleCount === totalCount && totalCount > 0
            ? "bg-green-50 text-green-800 border border-green-200"
            : accessibleCount === 0
            ? "bg-red-50 text-red-800 border border-red-200"
            : "bg-yellow-50 text-yellow-800 border border-yellow-200"
        }`}
      >
        {data.summary || `${accessibleCount} of ${totalCount} AI providers can access your site`}
      </div>

      {/* Comparison table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2 pr-3 font-medium text-muted-foreground">Check</th>
              <th className="text-left py-2 px-3 font-medium text-muted-foreground">
                Ground Truth
              </th>
              {data.providers.map((p) => (
                <th key={p.provider_name} className="text-left py-2 px-3 font-medium">
                  {providerLabels[p.provider_name] || p.provider_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {checkTypes.map((checkType) => {
              const gtValue = getGroundTruthValue(checkType, gtPages);
              if (!gtValue && !data.providers.some((p) => getCheck(p, checkType))) return null;

              return (
                <tr key={checkType} className="border-b border-border/50">
                  <td className="py-2 pr-3 font-medium">{checkLabels[checkType]}</td>
                  <td className="py-2 px-3 text-muted-foreground">{gtValue || "N/A"}</td>
                  {data.providers.map((p) => {
                    const check = getCheck(p, checkType);
                    return (
                      <td key={p.provider_name} className="py-2 px-3">
                        <CheckCell check={check} />
                      </td>
                    );
                  })}
                </tr>
              );
            })}

            {/* Status row */}
            <tr className="border-t-2">
              <td className="py-2 pr-3 font-semibold">Status</td>
              <td className="py-2 px-3 text-muted-foreground">---</td>
              {data.providers.map((p) => (
                <td key={p.provider_name} className="py-2 px-3">
                  <AccessBadge access={p.overall_access} score={p.access_score} />
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {/* Expandable raw responses */}
      <div className="mt-4 space-y-2">
        {data.providers.map((p) => (
          <div key={p.provider_name} className="border rounded-md">
            <button
              onClick={() =>
                setExpandedProvider(expandedProvider === p.provider_name ? null : p.provider_name)
              }
              className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-muted/50"
            >
              <span className="font-medium">
                {providerLabels[p.provider_name] || p.provider_name} raw response
              </span>
              {expandedProvider === p.provider_name ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>
            {expandedProvider === p.provider_name && (
              <div className="px-3 pb-3">
                <pre className="text-[10px] bg-muted/30 p-2 rounded whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {p.response_text || p.error || "No response"}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Source info */}
      {gt && (
        <div className="mt-3 text-[10px] text-muted-foreground">
          Ground truth source: {gt.source} ({gt.crawl_time}s)
        </div>
      )}
    </div>
  );
}

function getGroundTruthValue(
  checkType: string,
  gtPages: Record<string, GroundTruthPage | undefined>
): string {
  switch (checkType) {
    case "robots": {
      const p = gtPages["robots"];
      if (!p) return "";
      if (!p.accessible) return "Not found";
      if (p.raw_content) {
        const lines = p.raw_content.split("\n").slice(0, 3);
        return lines.join(" | ");
      }
      const blocked = Object.entries(p.robots_rules)
        .filter(([, v]) => v === "blocked")
        .map(([k]) => k);
      return blocked.length > 0 ? `Blocks: ${blocked.join(", ")}` : "No AI blocks";
    }
    case "inventory": {
      const p = gtPages["srp"];
      if (!p) return "";
      if (!p.accessible) return "Not accessible";
      return p.raw_content || `${p.vehicle_count} vehicles`;
    }
    case "vdp_price": {
      const p = gtPages["vdp"];
      if (!p) return "";
      return p.price || "No price found";
    }
    case "vdp_vin": {
      const p = gtPages["vdp"];
      if (!p) return "";
      return p.vin || "No VIN found";
    }
    case "sitemap": {
      const p = gtPages["sitemap"];
      if (!p) return "";
      if (!p.accessible) return "Not found";
      const parts = [`${p.sitemap_url_count} URLs`];
      if (p.raw_content) {
        const urls = p.raw_content.split("\n").slice(0, 2);
        parts.push(urls.map((u) => u.split("/").pop() || u).join(", "));
      }
      return parts.join(" — ");
    }
    default:
      return "";
  }
}

function getCheck(provider: AIProviderVerificationV2, checkType: string): AIVerifyCheck | null {
  return provider.checks.find((c) => c.check_type === checkType) || null;
}

function CheckCell({ check }: { check: AIVerifyCheck | null }) {
  if (!check) return <span className="text-muted-foreground">-</span>;

  if (check.could_access === false) {
    return (
      <span className="inline-flex items-center gap-1 text-red-600 font-medium" title="AI could not access this page">
        <X className="w-3 h-3" /> BLOCKED
      </span>
    );
  }

  if (check.could_access === true) {
    const tooltip = check.data_expected
      ? `Expected: ${check.data_expected}\nReturned: ${check.data_returned}`
      : check.data_returned;
    const scoreLabel = check.match_score >= 0.8 ? "" : ` (${Math.round(check.match_score * 100)}%)`;

    if (check.match_score >= 0.8) {
      return (
        <span className="inline-flex items-center gap-1 text-green-600" title={tooltip}>
          <Check className="w-3 h-3" />
          {check.data_returned ? (
            <span className="truncate max-w-[120px]">
              {check.data_returned.substring(0, 40)}
            </span>
          ) : (
            "Match"
          )}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-yellow-600" title={tooltip}>
        <AlertCircle className="w-3 h-3" />
        {check.data_returned ? (
          <span className="truncate max-w-[120px]">
            {check.data_returned.substring(0, 40)}{scoreLabel}
          </span>
        ) : (
          `Partial${scoreLabel}`
        )}
      </span>
    );
  }

  return <span className="text-muted-foreground">N/A</span>;
}

function AccessBadge({ access, score }: { access: string; score: number }) {
  const styles: Record<string, string> = {
    full: "bg-green-100 text-green-800 border-green-200",
    partial: "bg-yellow-100 text-yellow-800 border-yellow-200",
    blocked: "bg-red-100 text-red-800 border-red-200",
    error: "bg-gray-100 text-gray-600 border-gray-200",
    unknown: "bg-gray-100 text-gray-600 border-gray-200",
  };

  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border uppercase ${
        styles[access] || styles.unknown
      }`}
    >
      {access} ({score}/10)
    </span>
  );
}

// ── V1 Card (legacy fallback) ──

function LiveVerifyCardV1({ data }: { data: AILiveVerifyResult }) {
  if (data.providers.length === 0) return null;

  return (
    <div className="p-6 rounded-lg border bg-card">
      <h2 className="text-lg font-semibold mb-1">Live AI Verification</h2>
      <p className="text-xs text-muted-foreground mb-4">
        Real AI APIs attempted to access the VDP and retrieve vehicle data
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {data.providers.map((p) => (
          <div
            key={p.provider_name}
            className={`p-4 rounded-md border ${
              p.could_access === true
                ? "border-green-200 bg-green-50/30"
                : p.could_access === false
                ? "border-red-200 bg-red-50/30"
                : "border-yellow-200 bg-yellow-50/30"
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <AccessIcon access={p.could_access} />
              <span className="font-medium capitalize">{p.provider_name}</span>
            </div>
            <div className="text-xs space-y-1">
              {p.could_access === true && <div className="text-green-700">Can access VDP</div>}
              {p.could_access === false && <div className="text-red-700">Blocked from VDP</div>}
              {p.could_access === null && !p.error && (
                <div className="text-yellow-700">Inconclusive</div>
              )}
              {p.error && (
                <div className="text-red-600 truncate" title={p.error}>
                  Error: {p.error}
                </div>
              )}
              {p.returned_price && (
                <div className="flex items-center gap-1">
                  <span className="text-muted-foreground">Price:</span>
                  <span>{p.returned_price}</span>
                  {p.price_matches ? (
                    <Check className="w-3 h-3 text-green-500" />
                  ) : (
                    <X className="w-3 h-3 text-red-400" />
                  )}
                </div>
              )}
              {p.returned_vin && (
                <div className="flex items-center gap-1">
                  <span className="text-muted-foreground">VIN:</span>
                  <span className="font-mono text-[10px]">{p.returned_vin}</span>
                  {p.vin_matches ? (
                    <Check className="w-3 h-3 text-green-500" />
                  ) : (
                    <X className="w-3 h-3 text-red-400" />
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {data.ground_truth_used && (
        <div className="mt-3 text-xs text-muted-foreground">
          Ground truth: {data.ground_truth_used.expected_price}
          {data.ground_truth_used.expected_vin && (
            <> / {data.ground_truth_used.expected_vin}</>
          )}
        </div>
      )}
    </div>
  );
}

function AccessIcon({ access }: { access: boolean | null }) {
  if (access === true) return <Check className="w-5 h-5 text-green-500 shrink-0" />;
  if (access === false) return <X className="w-5 h-5 text-red-500 shrink-0" />;
  return <AlertCircle className="w-5 h-5 text-yellow-500 shrink-0" />;
}
