import type { ScoreResponse } from "../lib/api";
import { GRADE_COLORS } from "../lib/constants";

interface ScoreCardProps {
  score: ScoreResponse;
}

export default function ScoreCard({ score }: ScoreCardProps) {
  const gradeClass = GRADE_COLORS[score.grade] || GRADE_COLORS["F"];

  return (
    <div className="p-8 rounded-lg border bg-card text-center">
      <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full border-4 ${gradeClass} text-4xl font-bold mb-4`}>
        {score.grade}
      </div>
      <div className="text-5xl font-bold mb-2">{score.total_score}</div>
      <div className="text-lg text-muted-foreground mb-1">out of {score.max_score}</div>
      <div className="text-sm font-medium text-muted-foreground">{score.grade_label}</div>
    </div>
  );
}
