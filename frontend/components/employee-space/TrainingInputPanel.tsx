'use client';

import { FileUploadSection } from '@/components/employee-space/FileUploadSection';
import { JsonTrainingEditor } from '@/components/employee-space/JsonTrainingEditor';
import { TextTrainingEditor } from '@/components/employee-space/TextTrainingEditor';
import { TrainingTypeSelector } from '@/components/employee-space/TrainingTypeSelector';
import { getBusinessModelLabel, type BusinessModelKey } from '@/lib/dashboard/business-models';
import { platformPrimaryButtonClassName } from '@/lib/platform-primary';
import type { JsonValidationResult } from '@/lib/employee-space/json-training';
import type { TrainingFileMetadata, TrainingSourceType } from '@/lib/employee-space/types';

const TRAINING_HINT_MESSAGE =
  'Save uploads and text/JSON to your account with Start Training. Model indexing and training execution are not available in this phase.';

type TrainingInputPanelProps = {
  selectedModelKey: BusinessModelKey | null;
  trainingType: TrainingSourceType;
  onTrainingTypeChange: (type: TrainingSourceType) => void;
  fileTitle: string;
  onFileTitleChange: (value: string) => void;
  fileTitleError: string | null;
  selectedFiles: TrainingFileMetadata[];
  fileError: string | null;
  onFilesSelected: (files: FileList | File[]) => void;
  onRemoveFile: (id: string) => void;
  textTitle: string;
  textContent: string;
  onTextTitleChange: (value: string) => void;
  onTextContentChange: (value: string) => void;
  onClearText: () => void;
  textError: string | null;
  jsonTitle: string;
  jsonContent: string;
  jsonValidation: JsonValidationResult;
  onJsonTitleChange: (value: string) => void;
  onJsonContentChange: (value: string) => void;
  onClearJson: () => void;
  canStartTraining: boolean;
  isSubmitting: boolean;
  integrationNotice: string | null;
  submitError: string | null;
  onStartTraining: () => void;
};

export function TrainingInputPanel({
  selectedModelKey,
  trainingType,
  onTrainingTypeChange,
  fileTitle,
  onFileTitleChange,
  fileTitleError,
  selectedFiles,
  fileError,
  onFilesSelected,
  onRemoveFile,
  textTitle,
  textContent,
  onTextTitleChange,
  onTextContentChange,
  onClearText,
  textError,
  jsonTitle,
  jsonContent,
  jsonValidation,
  onJsonTitleChange,
  onJsonContentChange,
  onClearJson,
  canStartTraining,
  isSubmitting,
  integrationNotice,
  submitError,
  onStartTraining,
}: TrainingInputPanelProps) {
  const modelLabel = selectedModelKey ? getBusinessModelLabel(selectedModelKey) : null;

  return (
    <aside
      className="flex min-h-0 flex-col rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
      data-testid="training-input-panel"
      aria-label="Train model"
    >
      <h2 className="text-sm font-semibold text-zinc-900">Train Model</h2>
      <p className="mt-1 text-xs text-zinc-600">
        File upload, text input, and JSON input use the model selected in the left panel.
      </p>

      {modelLabel ? (
        <p
          className="mt-3 rounded-lg bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-900"
          data-testid="training-target-model"
        >
          Training target: {modelLabel}
        </p>
      ) : (
        <p className="mt-3 text-xs text-amber-800" data-testid="training-target-model-missing">
          Select a model on the left before adding training data.
        </p>
      )}

      <div className="mt-4">
        <TrainingTypeSelector value={trainingType} onChange={onTrainingTypeChange} />
      </div>

      <div className="mt-4 min-h-0 flex-1 space-y-4 overflow-y-auto">
        {trainingType === 'file' ? (
          <FileUploadSection
            fileTitle={fileTitle}
            onFileTitleChange={onFileTitleChange}
            fileTitleError={fileTitleError}
            selectedFiles={selectedFiles}
            fileError={fileError}
            dropzoneDisabled={!selectedModelKey}
            onFilesSelected={onFilesSelected}
            onRemoveFile={onRemoveFile}
          />
        ) : null}
        {trainingType === 'text' ? (
          <TextTrainingEditor
            title={textTitle}
            content={textContent}
            onTitleChange={onTextTitleChange}
            onContentChange={onTextContentChange}
            onClear={onClearText}
            errorMessage={textError}
          />
        ) : null}
        {trainingType === 'json' ? (
          <JsonTrainingEditor
            title={jsonTitle}
            content={jsonContent}
            modelLabel={modelLabel}
            onTitleChange={onJsonTitleChange}
            onContentChange={onJsonContentChange}
            onClear={onClearJson}
            validation={jsonValidation}
          />
        ) : null}
      </div>

      <div className="mt-4 flex flex-col gap-3 border-t border-zinc-100 pt-4">
        <button
          type="button"
          data-testid="start-training-button"
          disabled={!canStartTraining || isSubmitting}
          onClick={onStartTraining}
          className={`cursor-pointer px-5 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-300 disabled:text-zinc-600 ${platformPrimaryButtonClassName}`}
        >
          {isSubmitting ? 'Saving…' : 'Start Training'}
        </button>
        {isSubmitting ? (
          <p className="text-sm text-zinc-600" data-testid="training-submitting" role="status">
            Uploading and saving to your account…
          </p>
        ) : null}
        {submitError ? (
          <p role="alert" data-testid="training-submit-error" className="text-sm text-red-600">
            {submitError}
          </p>
        ) : null}
        {integrationNotice ? (
          <p role="status" data-testid="training-integration-notice" className="text-sm text-emerald-800">
            {integrationNotice}
          </p>
        ) : (
          <p className="text-xs text-zinc-500" data-testid="training-phase-hint">
            {TRAINING_HINT_MESSAGE}
          </p>
        )}
      </div>
    </aside>
  );
}
