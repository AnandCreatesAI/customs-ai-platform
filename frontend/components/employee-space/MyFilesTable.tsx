'use client';

import { useMemo, useState } from 'react';

import { TrainingStatusBadge } from '@/components/employee-space/TrainingStatusBadge';
import { getBusinessModelLabel, type BusinessModelKey } from '@/lib/dashboard/business-models';
import { DEMO_MANAGED_FILES } from '@/lib/employee-space/demo-data';
import { formatFileSize } from '@/lib/employee-space/format';
import type { DemoManagedFile, TrainingStatus } from '@/lib/employee-space/types';

export function MyFilesTable() {
  const [files, setFiles] = useState<DemoManagedFile[]>(DEMO_MANAGED_FILES);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<TrainingStatus | 'all'>('all');
  const [modelFilter, setModelFilter] = useState<BusinessModelKey | 'all'>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return files.filter((file) => {
      if (statusFilter !== 'all' && file.status !== statusFilter) {
        return false;
      }
      if (modelFilter !== 'all' && file.modelKey !== modelFilter) {
        return false;
      }
      if (query && !file.name.toLowerCase().includes(query)) {
        return false;
      }
      return true;
    });
  }, [files, modelFilter, search, statusFilter]);

  const selected = files.find((file) => file.id === selectedId) ?? null;

  function handleDelete(file: DemoManagedFile) {
    const confirmed = window.confirm(`Remove demo file "${file.name}" from this view?`);
    if (!confirmed) {
      return;
    }
    setFiles((current) => current.filter((entry) => entry.id !== file.id));
    if (selectedId === file.id) {
      setSelectedId(null);
    }
  }

  return (
    <div className="space-y-4" data-testid="my-files-tab">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-1 flex-col gap-3 sm:flex-row">
          <input
            type="search"
            data-testid="my-files-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search files"
            aria-label="Search files"
            className="w-full max-w-xs rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          />
          <select
            data-testid="my-files-status-filter"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as TrainingStatus | 'all')}
            aria-label="Filter by status"
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="trained">Trained</option>
            <option value="failed">Failed</option>
          </select>
          <select
            data-testid="my-files-model-filter"
            value={modelFilter}
            onChange={(event) => setModelFilter(event.target.value as BusinessModelKey | 'all')}
            aria-label="Filter by model"
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          >
            <option value="all">All models</option>
            <option value="user">User Model</option>
            <option value="ebooks">eBooks Model</option>
            <option value="employee">Employee Model</option>
            <option value="hs_code">HS Code Model</option>
          </select>
        </div>
        <p className="text-xs text-zinc-500">Demonstration file records only</p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-4 py-3 font-semibold">File</th>
              <th className="px-4 py-3 font-semibold">Type</th>
              <th className="px-4 py-3 font-semibold">Size</th>
              <th className="px-4 py-3 font-semibold">Model</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Uploaded</th>
              <th className="px-4 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((file) => (
              <tr key={file.id} className="border-b border-zinc-100 last:border-0">
                <td className="px-4 py-3 font-medium text-zinc-900">{file.name}</td>
                <td className="px-4 py-3 text-zinc-600">{file.extension.toUpperCase()}</td>
                <td className="px-4 py-3 text-zinc-600">{formatFileSize(file.sizeBytes)}</td>
                <td className="px-4 py-3 text-zinc-600">{getBusinessModelLabel(file.modelKey)}</td>
                <td className="px-4 py-3">
                  <TrainingStatusBadge status={file.status} />
                </td>
                <td className="px-4 py-3 text-zinc-600">
                  {new Date(file.uploadedAt).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      data-testid={`my-files-view-${file.id}`}
                      onClick={() => setSelectedId(file.id)}
                      className="cursor-pointer text-xs font-medium text-indigo-700 hover:underline"
                    >
                      View
                    </button>
                    <button
                      type="button"
                      data-testid={`my-files-delete-${file.id}`}
                      onClick={() => handleDelete(file)}
                      className="cursor-pointer text-xs font-medium text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 ? (
          <p className="px-4 py-6 text-sm text-zinc-500">No files match your filters.</p>
        ) : null}
      </div>

      {selected ? (
        <div
          className="rounded-xl border border-zinc-200 bg-white p-4 text-sm shadow-sm"
          data-testid="my-files-detail"
        >
          <h3 className="font-semibold text-zinc-900">{selected.name}</h3>
          <p className="mt-2 text-zinc-600">Model: {getBusinessModelLabel(selected.modelKey)}</p>
          <p className="text-zinc-600">Status: {selected.status}</p>
          <p className="mt-2 text-xs text-zinc-500">Demo record — not stored in PostgreSQL.</p>
        </div>
      ) : null}
    </div>
  );
}
