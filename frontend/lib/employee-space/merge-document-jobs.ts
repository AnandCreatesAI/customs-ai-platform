import type { TrainingJobSummary } from '@/services/training-job-service';
import type { UserTrainingDocument } from '@/lib/employee-space/types';

export function latestJobByDocumentId(
  jobs: TrainingJobSummary[],
): Map<string, TrainingJobSummary> {
  const map = new Map<string, TrainingJobSummary>();
  for (const job of jobs) {
    const existing = map.get(job.document_id);
    if (!existing) {
      map.set(job.document_id, job);
      continue;
    }
    const existingTime = Date.parse(existing.updated_at);
    const jobTime = Date.parse(job.updated_at);
    if (jobTime >= existingTime) {
      map.set(job.document_id, job);
    }
  }
  return map;
}

export function attachTrainingJobsToDocuments(
  documents: UserTrainingDocument[],
  jobs: TrainingJobSummary[],
): UserTrainingDocument[] {
  const jobByDocument = latestJobByDocumentId(jobs);
  return documents.map((document) => {
    const job = jobByDocument.get(document.id);
    if (!job) {
      return document;
    }
    const failureParts: string[] = [];
    if (job.error_message?.trim()) {
      failureParts.push(job.error_message.trim());
    }
    if (job.dispatch_error?.trim()) {
      failureParts.push(`Dispatch: ${job.dispatch_error.trim()}`);
    }
    return {
      ...document,
      trainingJob: {
        id: job.id,
        status: job.status,
        progress: job.progress,
        currentStage: job.current_stage,
        dispatchError: job.dispatch_error?.trim() || null,
        errorMessage: job.error_message?.trim() || null,
        updatedAt: job.updated_at,
        retryCount: job.retry_count,
      },
      failureReason:
        failureParts.length > 0 ? failureParts.join(' ') : document.failureReason,
    };
  });
}
