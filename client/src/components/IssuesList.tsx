import type { Issue } from "../lib/api";
import { SEVERITY_COLORS } from "../lib/constants";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";

interface IssuesListProps {
  issues: Issue[];
  recommendations: string[];
}

export default function IssuesList({ issues, recommendations }: IssuesListProps) {
  const severityIcons = {
    critical: <AlertTriangle className="w-4 h-4" />,
    warning: <AlertCircle className="w-4 h-4" />,
    info: <Info className="w-4 h-4" />,
  };

  return (
    <div className="space-y-6">
      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="p-6 rounded-lg border bg-card">
          <h2 className="text-lg font-semibold mb-3">Recommendations</h2>
          <ol className="space-y-2 list-decimal list-inside">
            {recommendations.map((rec, i) => (
              <li key={i} className="text-sm">{rec}</li>
            ))}
          </ol>
        </div>
      )}

      {/* Issues */}
      {issues.length > 0 && (
        <div className="p-6 rounded-lg border bg-card">
          <h2 className="text-lg font-semibold mb-3">Issues Found ({issues.length})</h2>
          <div className="space-y-2">
            {issues.map((issue, i) => {
              const colorClass = SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.info;
              const icon = severityIcons[issue.severity as keyof typeof severityIcons] || severityIcons.info;

              return (
                <div key={i} className={`flex gap-3 p-3 rounded-md border ${colorClass}`}>
                  <div className="shrink-0 mt-0.5">{icon}</div>
                  <div>
                    <div className="text-sm font-medium">{issue.message}</div>
                    {issue.recommendation && (
                      <div className="text-xs mt-1 opacity-80">{issue.recommendation}</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
