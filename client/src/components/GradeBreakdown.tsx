import type { CategoryScore } from "../lib/api";
import { CATEGORY_COLORS } from "../lib/constants";

interface GradeBreakdownProps {
  categories: CategoryScore[];
}

export default function GradeBreakdown({ categories }: GradeBreakdownProps) {
  return (
    <div className="p-6 rounded-lg border bg-card">
      <h2 className="text-lg font-semibold mb-4">Score Breakdown</h2>
      <div className="space-y-4">
        {categories.map((cat) => {
          const pct = Math.round((cat.score / cat.max_score) * 100);
          const barColor = CATEGORY_COLORS[cat.name] || "bg-gray-400";

          return (
            <div key={cat.name}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium">{cat.name}</span>
                <span className="text-muted-foreground">
                  {cat.score}/{cat.max_score}
                </span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2.5">
                <div
                  className={`h-2.5 rounded-full transition-all ${barColor}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              {cat.details.length > 0 && (
                <ul className="mt-1 text-xs text-muted-foreground space-y-0.5">
                  {cat.details.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
