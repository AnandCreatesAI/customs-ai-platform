type TrainingProgressBarProps = {
  percent: number;
  barClassName?: string;
  label?: string;
  /** @deprecated Demo rows only */
  status?: 'pending' | 'running' | 'trained' | 'failed';
};

function barClassFromLegacyStatus(status?: TrainingProgressBarProps['status']): string {
  if (status === 'trained') {
    return 'bg-emerald-500';
  }
  if (status === 'failed') {
    return 'bg-red-400';
  }
  if (status === 'pending') {
    return 'bg-amber-500';
  }
  return 'bg-amber-500';
}

export function TrainingProgressBar({
  percent,
  barClassName,
  label = 'Progress',
  status,
}: TrainingProgressBarProps) {
  const resolvedBarClass = barClassName ?? barClassFromLegacyStatus(status);
  const clamped = Math.max(0, Math.min(100, percent));

  return (
    <div className="space-y-1" data-testid="training-progress-bar">
      <div className="flex items-center justify-between text-xs text-zinc-600">
        <span>{label}</span>
        <span data-testid="training-progress-percent">{clamped}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-zinc-200"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full transition-all duration-300 ${resolvedBarClass}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
