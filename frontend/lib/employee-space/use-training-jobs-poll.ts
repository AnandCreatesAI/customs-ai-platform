'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import {
  fetchTrainingJobs,
  isActiveTrainingJobStatus,
  type TrainingJobSummary,
} from '@/services/training-job-service';

const POLL_INTERVAL_MS = 4000;

export function useTrainingJobsPoll(selectedModelKey: BusinessModelKey | null) {
  const [jobs, setJobs] = useState<TrainingJobSummary[]>([]);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [jobsLoading, setJobsLoading] = useState(false);
  const requestIdRef = useRef(0);

  const reloadTrainingJobs = useCallback(async (modelKeyOverride?: BusinessModelKey | null) => {
    const modelKey = modelKeyOverride !== undefined ? modelKeyOverride : selectedModelKey;
    if (!modelKey) {
      setJobs([]);
      setJobsError(null);
      return;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setJobsLoading(true);

    const result = await fetchTrainingJobs({
      businessModel: modelKey,
      pageSize: 100,
    });

    if (requestIdRef.current !== requestId) {
      return;
    }

    setJobsLoading(false);

    if (!result.ok) {
      setJobsError(result.message);
      if (result.unauthenticated) {
        setJobs([]);
      }
      return;
    }

    setJobsError(null);
    setJobs(result.page.results);
  }, [selectedModelKey]);

  const hasActiveJobs = jobs.some((job) => isActiveTrainingJobStatus(job.status));

  useEffect(() => {
    if (!selectedModelKey || !hasActiveJobs) {
      return;
    }
    const timer = window.setInterval(() => {
      void reloadTrainingJobs();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [hasActiveJobs, reloadTrainingJobs, selectedModelKey]);

  return {
    trainingJobs: jobs,
    trainingJobsError: jobsError,
    trainingJobsLoading: jobsLoading,
    reloadTrainingJobs,
    hasActiveTrainingJobs: hasActiveJobs,
  };
}
