'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { attachTrainingJobsToDocuments } from '@/lib/employee-space/merge-document-jobs';
import { useTrainingJobsPoll } from '@/lib/employee-space/use-training-jobs-poll';
import {
  createTrainingJobs,
  type TrainingJobSummary,
} from '@/services/training-job-service';

import { ModelSelectionPanel } from '@/components/employee-space/ModelSelectionPanel';
import { MyDocumentsPanel } from '@/components/employee-space/MyDocumentsPanel';
import { TrainingInputPanel } from '@/components/employee-space/TrainingInputPanel';
import type { AuthUser } from '@/services/auth-service';
import {
  fetchDocuments,
  submitTrainingJson,
  submitTrainingText,
  uploadTrainingFiles,
} from '@/services/document-service';
import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import {
  mapDocumentRecordToUserDocument,
  mapDocumentsToRecentActivity,
} from '@/lib/employee-space/document-mapper';
import { validateTrainingJson } from '@/lib/employee-space/json-training';
import { mergeTrainingFiles } from '@/lib/employee-space/training-file-metadata';
import {
  TRAINING_JSON_MAX_CHARS,
  TRAINING_TEXT_MAX_CHARS,
} from '@/lib/employee-space/training-input-limits';
import type { TrainModelModalStep } from '@/components/employee-space/TrainModelModals';
import type { TrainingFileMetadata, TrainingSourceType, UserTrainingDocument } from '@/lib/employee-space/types';

const MODEL_CHANGE_CONFIRM_MESSAGE =
  'Changing the model will clear files, text, and JSON prepared for the current model. Continue?';

type EmployeeSpaceWorkspaceProps = {
  user: AuthUser;
};

function clearPendingTraining() {
  return {
    selectedFiles: [] as TrainingFileMetadata[],
    fileTitle: '',
    textTitle: '',
    textContent: '',
    jsonTitle: '',
    jsonContent: '',
    fileError: null as string | null,
    fileTitleError: null as string | null,
    textError: null as string | null,
  };
}

export function EmployeeSpaceWorkspace({ user }: EmployeeSpaceWorkspaceProps) {
  const [selectedModelKey, setSelectedModelKey] = useState<BusinessModelKey | null>(null);
  const [trainModalStep, setTrainModalStep] = useState<TrainModelModalStep>(null);
  const [selectedFiles, setSelectedFiles] = useState<TrainingFileMetadata[]>([]);
  const [fileTitle, setFileTitle] = useState('');
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileTitleError, setFileTitleError] = useState<string | null>(null);
  const [textTitle, setTextTitle] = useState('');
  const [textContent, setTextContent] = useState('');
  const [textError, setTextError] = useState<string | null>(null);
  const [jsonTitle, setJsonTitle] = useState('');
  const [jsonContent, setJsonContent] = useState('');
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [documents, setDocuments] = useState<UserTrainingDocument[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [documentsPage, setDocumentsPage] = useState(1);
  const [hasMoreDocuments, setHasMoreDocuments] = useState(false);
  const [loadingMoreDocuments, setLoadingMoreDocuments] = useState(false);

  const jsonValidation = useMemo(() => validateTrainingJson(jsonContent), [jsonContent]);

  const {
    trainingJobs,
    trainingJobsError,
    reloadTrainingJobs,
    hasActiveTrainingJobs,
  } = useTrainingJobsPoll(selectedModelKey);

  const documentsWithJobs = useMemo(
    () => attachTrainingJobsToDocuments(documents, trainingJobs),
    [documents, trainingJobs],
  );

  const recentActivity = useMemo(
    () => mapDocumentsToRecentActivity(documentsWithJobs),
    [documentsWithJobs],
  );

  const dispatchTrainingJobs = useCallback(
    async (modelKey: BusinessModelKey, documentIds: string[]): Promise<string | null> => {
      if (documentIds.length === 0) {
        return null;
      }
      const result = await createTrainingJobs({
        businessModel: modelKey,
        documentIds,
      });
      if (!result.ok) {
        return result.message;
      }
      await reloadTrainingJobs();
      const dispatchIssues = result.jobs
        .filter((job: TrainingJobSummary) => job.dispatch_error?.trim())
        .map((job) => `${job.document_id}: ${job.dispatch_error.trim()}`);
      if (dispatchIssues.length > 0) {
        return `Training queued but Celery dispatch failed for some jobs. ${dispatchIssues.join(' ')}`;
      }
      return null;
    },
    [reloadTrainingJobs],
  );

  const loadDocuments = useCallback(
    async (modelKey: BusinessModelKey | null, page = 1, append = false) => {
      if (!modelKey) {
        setDocuments([]);
        setHasMoreDocuments(false);
        setDocumentsPage(1);
        return;
      }

      if (append) {
        setLoadingMoreDocuments(true);
      } else {
        setDocumentsLoading(true);
        setDocumentsError(null);
      }

      const result = await fetchDocuments({
        page,
        pageSize: 20,
        businessModel: modelKey,
      });

      if (append) {
        setLoadingMoreDocuments(false);
      } else {
        setDocumentsLoading(false);
      }

      if (!result.ok) {
        if (result.unauthenticated) {
          setDocumentsError('Your session expired. Sign in again to load documents.');
        } else {
          setDocumentsError(result.message);
        }
        if (!append) {
          setDocuments([]);
        }
        return;
      }

      const mapped = result.page.results.map((record) =>
        mapDocumentRecordToUserDocument(record, user.id),
      );
      setDocuments((current) => (append ? [...current, ...mapped] : mapped));
      setDocumentsPage(page);
      setHasMoreDocuments(Boolean(result.page.next));
    },
    [user.id],
  );

  const hadActiveJobsRef = useRef(false);
  useEffect(() => {
    if (hadActiveJobsRef.current && !hasActiveTrainingJobs && selectedModelKey) {
      void loadDocuments(selectedModelKey, 1, false);
    }
    hadActiveJobsRef.current = hasActiveTrainingJobs;
  }, [hasActiveTrainingJobs, selectedModelKey, loadDocuments]);

  const hasPendingInput =
    selectedFiles.length > 0 ||
    fileTitle.trim().length > 0 ||
    textTitle.trim().length > 0 ||
    textContent.trim().length > 0 ||
    jsonTitle.trim().length > 0 ||
    jsonContent.trim().length > 0;

  const handleModelSelect = useCallback(
    (key: BusinessModelKey) => {
      if (isSubmitting) {
        return;
      }
      if (key === selectedModelKey) {
        return;
      }
      if (hasPendingInput && selectedModelKey) {
        const confirmed = window.confirm(MODEL_CHANGE_CONFIRM_MESSAGE);
        if (!confirmed) {
          return;
        }
        const cleared = clearPendingTraining();
        setSelectedFiles(cleared.selectedFiles);
        setFileTitle(cleared.fileTitle);
        setTextTitle(cleared.textTitle);
        setTextContent(cleared.textContent);
        setJsonTitle(cleared.jsonTitle);
        setJsonContent(cleared.jsonContent);
        setFileError(cleared.fileError);
        setFileTitleError(cleared.fileTitleError);
        setTextError(cleared.textError);
      }
      setSelectedModelKey(key);
      setSubmitError(null);
      setJsonError(null);
      void loadDocuments(key, 1, false);
      void reloadTrainingJobs(key);
    },
    [hasPendingInput, isSubmitting, loadDocuments, reloadTrainingJobs, selectedModelKey],
  );

  const canSubmitFile = useMemo(() => {
    if (!selectedModelKey || isSubmitting) {
      return false;
    }
    const hasFiles = selectedFiles.some((file) => file.modelKey === selectedModelKey);
    return hasFiles && fileTitle.trim().length > 0;
  }, [fileTitle, isSubmitting, selectedFiles, selectedModelKey]);

  const canSubmitText = useMemo(() => {
    if (!selectedModelKey || isSubmitting) {
      return false;
    }
    return textTitle.trim().length > 0 && textContent.trim().length > 0;
  }, [isSubmitting, selectedModelKey, textContent, textTitle]);

  const canSubmitJson = useMemo(() => {
    if (!selectedModelKey || isSubmitting) {
      return false;
    }
    return jsonTitle.trim().length > 0 && jsonValidation.status === 'valid';
  }, [isSubmitting, jsonTitle, jsonValidation.status, selectedModelKey]);

  const stagedTextLabel = useMemo(() => {
    if (textContent.trim().length === 0) {
      return null;
    }
    return textTitle.trim() || 'Untitled text training';
  }, [textContent, textTitle]);

  const stagedJsonLabel = useMemo(() => {
    if (jsonContent.trim().length === 0) {
      return null;
    }
    return jsonTitle.trim() || 'Untitled JSON training';
  }, [jsonContent, jsonTitle]);

  function addFiles(incoming: FileList | File[]) {
    if (!selectedModelKey) {
      setFileError('Select a model before uploading files.');
      return;
    }
    const modelKey = selectedModelKey;
    const incomingFiles = Array.from(incoming);
    setSelectedFiles((current) => {
      const { files, errors } = mergeTrainingFiles(current, incomingFiles, modelKey);
      setFileError(errors.length > 0 ? errors.join(' ') : null);
      return files;
    });
  }

  async function handleSubmitTraining(source: TrainingSourceType) {
    setSubmitError(null);
    setTextError(null);
    setJsonError(null);
    setFileTitleError(null);
    setFileError(null);

    if (!selectedModelKey || isSubmitting) {
      return;
    }

    const modelKey = selectedModelKey;

    if (source === 'file') {
      const filesForModel = selectedFiles.filter((file) => file.modelKey === modelKey);
      if (filesForModel.length === 0) {
        return;
      }
      if (fileTitle.trim().length === 0) {
        setFileTitleError('Enter a file title for the selected documents.');
        return;
      }

      setIsSubmitting(true);
      const uploadErrors: string[] = [];

      try {
        const uploadResult = await uploadTrainingFiles({
          businessModel: modelKey,
          title: fileTitle.trim(),
          files: filesForModel.map((entry) => entry.file),
        });
        if (!uploadResult.ok) {
          if (uploadResult.unauthenticated) {
            setSubmitError('Your session expired. Sign in again to upload files.');
            return;
          }
          setFileError(uploadResult.message);
          return;
        }

        const createdNames = new Set<string>();
        const createdDocumentIds: string[] = [];
        for (const entry of uploadResult.data.results) {
          if (entry.status === 'created') {
            createdNames.add(entry.document.original_filename);
            createdDocumentIds.push(entry.document.id);
          } else {
            uploadErrors.push(`${entry.filename}: ${entry.error}`);
          }
        }

        if (uploadErrors.length > 0) {
          setFileError(uploadErrors.join(' '));
        }

        if (createdNames.size > 0) {
          await loadDocuments(modelKey, 1, false);
          const trainError = await dispatchTrainingJobs(modelKey, createdDocumentIds);
          if (trainError) {
            setSubmitError(trainError);
          }
          setSelectedFiles((current) =>
            current.filter(
              (file) => file.modelKey !== modelKey || !createdNames.has(file.name),
            ),
          );
          if (uploadErrors.length === 0) {
            setFileTitle('');
            setTrainModalStep(null);
          }
        }
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (source === 'text') {
      if (!textTitle.trim()) {
        setTextError('Title is required.');
        return;
      }
      if (textContent.trim().length === 0) {
        setTextError('Enter training text content.');
        return;
      }
      if (textContent.length > TRAINING_TEXT_MAX_CHARS) {
        setTextError('Text content exceeds the configured character limit.');
        return;
      }

      setIsSubmitting(true);
      try {
        const textResult = await submitTrainingText({
          businessModel: modelKey,
          title: textTitle.trim(),
          content: textContent,
        });
        if (!textResult.ok) {
          setTextError(textResult.message);
          return;
        }
        setTextTitle('');
        setTextContent('');
        await loadDocuments(modelKey, 1, false);
        const trainError = await dispatchTrainingJobs(modelKey, [textResult.data.document.id]);
        if (trainError) {
          setSubmitError(trainError);
        }
        setTrainModalStep(null);
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (source === 'json') {
      if (!jsonTitle.trim()) {
        setJsonError('JSON title is required.');
        return;
      }
      if (jsonValidation.status !== 'valid') {
        setJsonError('Enter valid JSON before saving.');
        return;
      }
      if (jsonContent.length > TRAINING_JSON_MAX_CHARS) {
        setJsonError('JSON content exceeds the configured character limit.');
        return;
      }

      setIsSubmitting(true);
      try {
        const jsonResult = await submitTrainingJson({
          businessModel: modelKey,
          title: jsonTitle.trim(),
          content: jsonContent.trim(),
        });
        if (!jsonResult.ok) {
          setJsonError(jsonResult.message);
          return;
        }
        setJsonTitle('');
        setJsonContent('');
        await loadDocuments(modelKey, 1, false);
        const trainError = await dispatchTrainingJobs(modelKey, [jsonResult.data.document.id]);
        if (trainError) {
          setSubmitError(trainError);
        }
        setTrainModalStep(null);
      } finally {
        setIsSubmitting(false);
      }
    }
  }

  return (
    <div
      className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-y-auto p-4 md:p-5 xl:grid-cols-[minmax(240px,280px)_minmax(0,1fr)_minmax(300px,360px)] xl:overflow-hidden"
      data-testid="employee-space-workspace"
      data-layout="three-column"
    >
      <ModelSelectionPanel selectedKey={selectedModelKey} onSelect={handleModelSelect} />
      <MyDocumentsPanel
        userId={user.id}
        documents={documentsWithJobs}
        documentsLoading={documentsLoading}
        documentsError={documentsError}
        trainingJobsError={trainingJobsError}
        onRetryTrainingJobs={() => void reloadTrainingJobs()}
        onRetryLoad={() => {
          void loadDocuments(selectedModelKey, 1, false);
          void reloadTrainingJobs();
        }}
        hasMoreDocuments={hasMoreDocuments}
        onLoadMore={() => void loadDocuments(selectedModelKey, documentsPage + 1, true)}
        loadingMore={loadingMoreDocuments}
        stagedFiles={selectedFiles}
        stagedFileGroupTitle={
          selectedFiles.length > 0 && fileTitle.trim().length > 0 ? fileTitle.trim() : null
        }
        stagedTextLabel={stagedTextLabel}
        stagedTextModelKey={stagedTextLabel ? selectedModelKey : null}
        stagedJsonLabel={stagedJsonLabel}
        stagedJsonModelKey={stagedJsonLabel ? selectedModelKey : null}
        recentActivity={recentActivity}
      />
      <TrainingInputPanel
        selectedModelKey={selectedModelKey}
        trainModalStep={trainModalStep}
        onTrainModalStepChange={setTrainModalStep}
        fileTitle={fileTitle}
        onFileTitleChange={(value) => {
          setFileTitle(value);
          setFileTitleError(null);
        }}
        fileTitleError={fileTitleError}
        selectedFiles={selectedFiles}
        fileError={fileError}
        onFilesSelected={addFiles}
        onRemoveFile={(id) => setSelectedFiles((current) => current.filter((file) => file.id !== id))}
        textTitle={textTitle}
        textContent={textContent}
        onTextTitleChange={setTextTitle}
        onTextContentChange={(value) => {
          setTextContent(value);
          setTextError(null);
        }}
        onClearText={() => {
          setTextTitle('');
          setTextContent('');
          setTextError(null);
        }}
        textError={textError}
        jsonTitle={jsonTitle}
        jsonContent={jsonContent}
        jsonValidation={jsonValidation}
        jsonError={jsonError}
        onJsonTitleChange={setJsonTitle}
        onJsonContentChange={(value) => {
          setJsonContent(value);
          setJsonError(null);
        }}
        onClearJson={() => {
          setJsonTitle('');
          setJsonContent('');
          setJsonError(null);
        }}
        canSubmitFile={canSubmitFile}
        canSubmitText={canSubmitText}
        canSubmitJson={canSubmitJson}
        isSubmitting={isSubmitting}
        submitError={submitError}
        onSubmitTraining={(source) => void handleSubmitTraining(source)}
      />
    </div>
  );
}
