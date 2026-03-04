import type { BotPermission } from "../lib/api";
import { Check, X, AlertCircle } from "lucide-react";

interface BotStatusGridProps {
  permissions: BotPermission[];
}

export default function BotStatusGrid({ permissions }: BotStatusGridProps) {
  if (!permissions || permissions.length === 0) return null;

  return (
    <div className="p-6 rounded-lg border bg-card">
      <h2 className="text-lg font-semibold mb-4">AI Bot Access</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {permissions.map((bot) => (
          <div
            key={bot.bot_name}
            className="flex items-center gap-3 p-3 rounded-md border text-sm"
          >
            <StatusIcon robots={bot.robots_status} http={bot.http_accessible} />
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">{bot.bot_name}</div>
              <div className="text-xs text-muted-foreground">{bot.details}</div>
            </div>
            <div className="flex gap-2 text-xs">
              <span
                className={`px-1.5 py-0.5 rounded ${
                  bot.robots_status === "allowed"
                    ? "bg-green-50 text-green-700"
                    : bot.robots_status === "blocked"
                    ? "bg-red-50 text-red-700"
                    : "bg-gray-50 text-gray-500"
                }`}
              >
                robots
              </span>
              <span
                className={`px-1.5 py-0.5 rounded ${
                  bot.http_accessible === true
                    ? "bg-green-50 text-green-700"
                    : bot.http_accessible === false
                    ? "bg-red-50 text-red-700"
                    : "bg-gray-50 text-gray-500"
                }`}
              >
                http
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusIcon({
  robots,
  http,
}: {
  robots: string;
  http: boolean | null;
}) {
  if (robots === "blocked" || http === false) {
    return <X className="w-5 h-5 text-red-500 shrink-0" />;
  }
  if (robots === "allowed" && http === true) {
    return <Check className="w-5 h-5 text-green-500 shrink-0" />;
  }
  return <AlertCircle className="w-5 h-5 text-yellow-500 shrink-0" />;
}
