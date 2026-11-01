'use client';

import { useMemo, useState } from 'react';

import { TrainingProgressBar } from '@/components/employee-space/TrainingProgressBar';
import { TrainingStatusBadge } from '@/components/employee-space/TrainingStatusBadge';
import { getBusinessModelLabel, type BusinessModelKey } from '@/lib/dashboard/business-models';
import { DEMO_TRAINING_HISTORY } from '@/lib/employee-space/demo-data';
import type { DemoTrainingHistoryRecord, TrainingStatus } from '@/lib/employee-space/types';

export function TrainingHistoryTable() {
  const [records] = useState<DemoTrainingHistoryRecord[]>(DEMO_TRAINING_HISTORY);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<TrainingStatus | 'all'>('all');
  const [modelFilter, setModelFilter] = useState<BusinessModelKey | 'all'>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return records.filter((record) => {
      if (statusFilter !== 'all' && record.status !== statusFilter) {
        return false;
      }
      if (modelFilter !== 'all' && record.modelKey !== modelFilter) {
        return false;
      }
      if (
        query &&
        !record.jobId.toLowerCase().includes(query) &&
        !record.sourceName.toLowerCase().includes(query)
      ) {
        return false;
      }
      return true;
    });
  }, [modelFilter, records, search, statusFilter]);

  const selected = records.find((record) => record.id === selectedId) ?? null;

  return (
    <div className="space-y-4" data-testid="training-history-tab">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-1 flex-col gap-3 sm:flex-row">
          <input
            type="search"
            data-testid="training-history-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search jobs or sources"
            aria-label="Search training history"
            className="w-full max-w-xs rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
          <select
            data-testid="training-history-status-filter"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as TrainingStatus | 'all')}
            aria-label="Filter by status"
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="trained">Trained</option>
            <option value="failed">Failed</option>
          </select>
          <select
            data-testid="training-history-model-filter"
            value={modelFilter}
            onChange={(event) => setModelFilter(event.target.value as BusinessModelKey | 'all')}
            aria-label="Filter by model"
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          >
            <option value="all">All models</option>
            <option value="user">User Model</option>
            <option value="ebooks">eBooks Model</option>
            <option value="employee">Employee Model</option>
            <option value="hs_code">HS Code Model</option>
          </select>
        </div>
        <p className="text-xs text-zinc-500">Demonstration training jobs only</p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Job ID</th>
              <th className="px-4 py-3 font-semibold">Model</th>
              <th className="px-4 py-3 font-semibold">Source</th>
              <th className="px-4 py-3 font-semibold">Started</th>
              <th className="px-4 py-3 font-semibold">Completed</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((record) => (
              <tr key={record.id} className="border-b border-zinc-100 last:border-0">
                <td className="px-4 py-3 font-mono text-xs text-zinc-800">{record.jobId}</td>
                <td className="px-4 py-3">{getBusinessModelLabel(record.modelKey)}</td>
                <td className="px-4 py-3 text-zinc-700">{record.sourceName}</td>
                <td className="px-4 py-3 text-zinc-600">
                  {new Date(record.startedAt).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-zinc-600">
                  {record.completedAt ? new Date(record.completedAt).toLocaleString() : '—'}
                </td>
                <td className="px-4 py-3">
                  <TrainingStatusBadge status={record.status} />
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    data-testid={`training-history-view-${record.id}`}
                    onClick={() => setSelectedId(record.id)}
                    className="cursor-pointer text-xs font-medium text-indigo-700 hover:underline"
                  >
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected ? (
        <div
          className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
          data-testid="training-history-detail"
        >
          <h3 className="font-semibold text-zinc-900">{selected.jobId}</h3>
          <TrainingProgressBar percent={selected.progressPercent} status={selected.status} />
          {selected.failureReason ? (
            <p className="text-sm text-red-600">{selected.failureReason}</p>
          ) : null}
          <p className="text-xs text-zinc-500">Demo job — not generated by a backend training API.</p>
        </div>
      ) : null}
    </div>
  );
}
