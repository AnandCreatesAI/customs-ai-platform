type TrainingProgressBarProps = {
  percent: number;
  status?: 'pending' | 'running' | 'trained' | 'failed';
};

export function TrainingProgressBar({ percent, status = 'running' }: TrainingProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, percent));
  const barColor =
    status === 'trained'
      ? 'bg-emerald-500'
      : status === 'failed'
        ? 'bg-red-400'
        : 'bg-amber-500';

  return (
    <div className="space-y-1" data-testid="training-progress-bar">
      <div className="flex items-center justify-between text-xs text-zinc-600">
        <span>Progress</span>
        <span data-testid="training-progress-percent">{clamped}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-zinc-200"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`h-full transition-all ${barColor}`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}
