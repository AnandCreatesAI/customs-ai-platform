'use client';

import { dashboardHeaderButtonClassName } from '@/lib/dashboard/dashboard-header-button-styles';
import { getBusinessModelLabel, DEFAULT_BUSINESS_MODEL_KEY } from '@/lib/dashboard/business-models';

/** Fixed header model label (replaces Select Model dropdown). */
export function UserModelIndicator() {
  const label = getBusinessModelLabel(DEFAULT_BUSINESS_MODEL_KEY);

  return (
    <div
      data-testid="user-model-indicator"
      aria-label={`Active model: ${label}`}
      className={`${dashboardHeaderButtonClassName} min-w-[9.5rem] cursor-default border-indigo-600`}
    >
      <span className="truncate">{label}</span>
    </div>
  );
}
