interface ProgressOverlayProps {
  progress: { step: string; percent: number };
}

export default function ProgressOverlay({ progress }: ProgressOverlayProps) {
  return (
    <div className="p-6 rounded-lg border bg-card mb-8">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium">{progress.step}</span>
        <span className="text-sm text-muted-foreground">{progress.percent}%</span>
      </div>
      <div className="w-full bg-secondary rounded-full h-2">
        <div
          className="bg-primary h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress.percent}%` }}
        />
      </div>
    </div>
  );
}
