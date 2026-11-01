'use client';

import type { ReactNode } from 'react';

import { ChevronRight, GraduationCap } from 'lucide-react';
import Link from 'next/link';

import { dashboardHeaderButtonClassName } from '@/lib/dashboard/dashboard-header-button-styles';
import { MenuIcon, PanelLeftOpenIcon } from '@/components/dashboard/icons';
import { ModelSelector } from '@/components/dashboard/ModelSelector';
import { UserModelIndicator } from '@/components/dashboard/UserModelIndicator';
import type { BusinessModelKey } from '@/lib/dashboard/business-models';

const EMPLOYEE_SPACE_HREF = '/dashboard/employee-space';

type DashboardHeaderProps = {
  mode?: 'public' | 'authenticated';
  selectedModelKey?: BusinessModelKey | null;
  onModelSelect?: (key: BusinessModelKey) => void;
  onToggleMobileSidebar: () => void;
  onExpandDesktopSidebar?: () => void;
  desktopSidebarCollapsed?: boolean;
  showSidebarControls?: boolean;
  showEmployeeSpace?: boolean;
  trailingActions?: ReactNode;
};

export function DashboardHeader({
  mode = 'authenticated',
  selectedModelKey = null,
  onModelSelect,
  onToggleMobileSidebar,
  onExpandDesktopSidebar,
  desktopSidebarCollapsed = false,
  showSidebarControls = true,
  showEmployeeSpace = true,
  trailingActions,
}: DashboardHeaderProps) {
  return (
    <header
      data-testid="dashboard-header"
      className="flex shrink-0 flex-wrap items-center gap-3 border-b border-zinc-200/90 bg-white px-4 py-2 shadow-sm"
    >
      {showSidebarControls ? (
        <>
          <button
            type="button"
            data-testid="sidebar-toggle"
            aria-label="Toggle sidebar"
            onClick={onToggleMobileSidebar}
            className="inline-flex rounded-lg p-2 text-zinc-600 transition hover:bg-zinc-100 md:hidden"
          >
            <MenuIcon className="h-5 w-5" />
          </button>

          {desktopSidebarCollapsed ? (
            <button
              type="button"
              data-testid="sidebar-expand"
              aria-label="Expand sidebar"
              onClick={onExpandDesktopSidebar}
              className="hidden rounded-lg p-2 text-zinc-600 transition hover:bg-zinc-100 md:inline-flex"
            >
              <PanelLeftOpenIcon className="h-5 w-5" />
            </button>
          ) : null}
        </>
      ) : null}

      <div
        className="flex flex-wrap items-center gap-3"
        data-testid="dashboard-header-controls"
      >
        {mode === 'public' ? (
          <UserModelIndicator />
        ) : (
          <ModelSelector
            selectedKey={selectedModelKey ?? null}
            onSelect={(key) => onModelSelect?.(key)}
            appearance="header"
          />
        )}
        {mode === 'authenticated' && showEmployeeSpace ? (
          <Link
            href={EMPLOYEE_SPACE_HREF}
            data-testid="header-employee-space"
            aria-label="Open Employee Space"
            className={dashboardHeaderButtonClassName}
          >
            <GraduationCap className="h-4 w-4 shrink-0 text-white" aria-hidden />
            <span className="truncate">Employee Space</span>
            <ChevronRight className="h-4 w-4 shrink-0 text-white" aria-hidden />
          </Link>
        ) : null}
      </div>

      {trailingActions ? (
        <div className="ml-auto flex shrink-0 items-center">{trailingActions}</div>
      ) : null}
    </header>
  );
}
