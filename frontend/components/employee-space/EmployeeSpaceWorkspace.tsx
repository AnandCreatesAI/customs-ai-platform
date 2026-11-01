'use client';

import { useCallback, useMemo, useState } from 'react';

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
import type { TrainingFileMetadata, TrainingSourceType, UserTrainingDocument } from '@/lib/employee-space/types';

const MODEL_CHANGE_CONFIRM_MESSAGE =
  'Changing the model will clear files, text, and JSON prepared for the current model. Continue?';

const TRAINING_SAVED_NOTICE =
  'Documents were saved to your account. Model training (indexing and execution) is not available in this phase.';

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
  const [trainingType, setTrainingType] = useState<TrainingSourceType>('file');
  const [selectedFiles, setSelectedFiles] = useState<TrainingFileMetadata[]>([]);
  const [fileTitle, setFileTitle] = useState('');
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileTitleError, setFileTitleError] = useState<string | null>(null);
  const [textTitle, setTextTitle] = useState('');
  const [textContent, setTextContent] = useState('');
  const [textError, setTextError] = useState<string | null>(null);
  const [jsonTitle, setJsonTitle] = useState('');
  const [jsonContent, setJsonContent] = useState('');
  const [integrationNotice, setIntegrationNotice] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [documents, setDocuments] = useState<UserTrainingDocument[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [documentsPage, setDocumentsPage] = useState(1);
  const [hasMoreDocuments, setHasMoreDocuments] = useState(false);
  const [loadingMoreDocuments, setLoadingMoreDocuments] = useState(false);

  const jsonValidation = useMemo(() => validateTrainingJson(jsonContent), [jsonContent]);

  const recentActivity = useMemo(
    () => mapDocumentsToRecentActivity(documents),
    [documents],
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
      setIntegrationNotice(null);
      setSubmitError(null);
      void loadDocuments(key, 1, false);
    },
    [hasPendingInput, isSubmitting, loadDocuments, selectedModelKey],
  );

  const canStartTraining = useMemo(() => {
    if (!selectedModelKey || isSubmitting) {
      return false;
    }
    const hasFiles = selectedFiles.some((file) => file.modelKey === selectedModelKey);
    const hasText = textContent.trim().length > 0;
    const hasValidJson = jsonValidation.status === 'valid';
    const filesReady = !hasFiles || fileTitle.trim().length > 0;
    return filesReady && (hasFiles || hasText || hasValidJson);
  }, [
    fileTitle,
    isSubmitting,
    jsonValidation.status,
    selectedFiles,
    selectedModelKey,
    textContent,
  ]);

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
    setSelectedFiles((current) => {
      const { files, errors } = mergeTrainingFiles(current, incoming, selectedModelKey);
      setFileError(errors.length > 0 ? errors.join(' ') : null);
      return files;
    });
  }

  async function handleStartTraining() {
    setIntegrationNotice(null);
    setSubmitError(null);
    setTextError(null);
    setFileTitleError(null);
    setFileError(null);

    if (!selectedModelKey || isSubmitting) {
      return;
    }

    const modelKey = selectedModelKey;
    const filesForModel = selectedFiles.filter((file) => file.modelKey === modelKey);
    const hasFiles = filesForModel.length > 0;
    const hasText = textContent.trim().length > 0;
    const hasValidJson = jsonValidation.status === 'valid';

    if (!hasFiles && !hasText && !hasValidJson) {
      return;
    }

    if (hasFiles && fileTitle.trim().length === 0) {
      setFileTitleError('Enter a file title for the selected documents.');
      return;
    }

    if (hasText) {
      if (!textTitle.trim()) {
        setTextError('Title is required.');
        return;
      }
      if (textContent.length > TRAINING_TEXT_MAX_CHARS) {
        setTextError('Text content exceeds the configured character limit.');
        return;
      }
    }

    if (hasValidJson) {
      if (!jsonTitle.trim()) {
        setSubmitError('JSON title is required.');
        return;
      }
      if (jsonContent.length > TRAINING_JSON_MAX_CHARS) {
        setSubmitError('JSON content exceeds the configured character limit.');
        return;
      }
    }

    setIsSubmitting(true);
    let anySuccess = false;
    const uploadErrors: string[] = [];

    try {
      if (hasFiles) {
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
        for (const entry of uploadResult.data.results) {
          if (entry.status === 'created') {
            anySuccess = true;
            createdNames.add(entry.document.original_filename);
          } else {
            uploadErrors.push(`${entry.filename}: ${entry.error}`);
          }
        }

        if (uploadErrors.length > 0) {
          setFileError(uploadErrors.join(' '));
        }

        if (createdNames.size > 0) {
          setSelectedFiles((current) =>
            current.filter(
              (file) =>
                file.modelKey !== modelKey || !createdNames.has(file.name),
            ),
          );
          if (uploadErrors.length === 0) {
            setFileTitle('');
          }
        }
      }

      if (hasText) {
        const textResult = await submitTrainingText({
          businessModel: modelKey,
          title: textTitle.trim(),
          content: textContent,
        });
        if (!textResult.ok) {
          setTextError(textResult.message);
          return;
        }
        anySuccess = true;
        setTextTitle('');
        setTextContent('');
      }

      if (hasValidJson) {
        const jsonResult = await submitTrainingJson({
          businessModel: modelKey,
          title: jsonTitle.trim(),
          content: jsonContent.trim(),
        });
        if (!jsonResult.ok) {
          setTextError(jsonResult.message);
          return;
        }
        anySuccess = true;
        setJsonTitle('');
        setJsonContent('');
      }

      if (anySuccess) {
        await loadDocuments(modelKey, 1, false);
        setIntegrationNotice(TRAINING_SAVED_NOTICE);
      }
    } finally {
      setIsSubmitting(false);
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
        documents={documents}
        documentsLoading={documentsLoading}
        documentsError={documentsError}
        onRetryLoad={() => void loadDocuments(selectedModelKey, 1, false)}
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
        trainingType={trainingType}
        onTrainingTypeChange={setTrainingType}
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
        onJsonTitleChange={setJsonTitle}
        onJsonContentChange={setJsonContent}
        onClearJson={() => {
          setJsonTitle('');
          setJsonContent('');
        }}
        canStartTraining={canStartTraining}
        isSubmitting={isSubmitting}
        integrationNotice={integrationNotice}
        submitError={submitError}
        onStartTraining={() => void handleStartTraining()}
      />
    </div>
  );
}
