'use client';

import {
  TrainModelModals,
  type TrainModelModalStep,
} from '@/components/employee-space/TrainModelModals';
import { getBusinessModelLabel, type BusinessModelKey } from '@/lib/dashboard/business-models';
import { platformPrimaryButtonClassName } from '@/lib/platform-primary';
import type { JsonValidationResult } from '@/lib/employee-space/json-training';
import type { TrainingFileMetadata, TrainingSourceType } from '@/lib/employee-space/types';

type TrainingInputPanelProps = {
  selectedModelKey: BusinessModelKey | null;
  trainModalStep: TrainModelModalStep;
  onTrainModalStepChange: (step: TrainModelModalStep) => void;
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
  jsonError: string | null;
  onJsonTitleChange: (value: string) => void;
  onJsonContentChange: (value: string) => void;
  onClearJson: () => void;
  canSubmitFile: boolean;
  canSubmitText: boolean;
  canSubmitJson: boolean;
  isSubmitting: boolean;
  submitError: string | null;
  onSubmitTraining: (source: TrainingSourceType) => void;
};

export function TrainingInputPanel({
  selectedModelKey,
  trainModalStep,
  onTrainModalStepChange,
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
  jsonError,
  onJsonTitleChange,
  onJsonContentChange,
  onClearJson,
  canSubmitFile,
  canSubmitText,
  canSubmitJson,
  isSubmitting,
  submitError,
  onSubmitTraining,
}: TrainingInputPanelProps) {
  const modelLabel = selectedModelKey ? getBusinessModelLabel(selectedModelKey) : null;

  return (
    <>
      <aside
        className="flex min-h-0 flex-col rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
        data-testid="training-input-panel"
        aria-label="Train model"
      >
        <h2 className="text-sm font-semibold text-zinc-900">Train Model</h2>
        <p className="mt-1 text-xs text-zinc-600">
          Add file, text, or JSON training for the business model selected on the left.
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

        <div className="mt-4 flex flex-1 flex-col justify-end gap-3 border-t border-zinc-100 pt-4">
          <button
            type="button"
            data-testid="open-train-model-modal"
            disabled={isSubmitting}
            onClick={() => onTrainModalStepChange('menu')}
            className={`cursor-pointer px-5 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-300 disabled:text-zinc-600 ${platformPrimaryButtonClassName}`}
          >
            Train Model
          </button>
          <p className="text-xs text-zinc-500">
            Uploads save documents and automatically queue TrainingJobs for the Celery pipeline.
          </p>
        </div>
      </aside>

      <TrainModelModals
        selectedModelKey={selectedModelKey}
        step={trainModalStep}
        onStepChange={onTrainModalStepChange}
        fileTitle={fileTitle}
        onFileTitleChange={onFileTitleChange}
        fileTitleError={fileTitleError}
        selectedFiles={selectedFiles}
        fileError={fileError}
        onFilesSelected={onFilesSelected}
        onRemoveFile={onRemoveFile}
        textTitle={textTitle}
        textContent={textContent}
        onTextTitleChange={onTextTitleChange}
        onTextContentChange={onTextContentChange}
        onClearText={onClearText}
        textError={textError}
        jsonTitle={jsonTitle}
        jsonContent={jsonContent}
        jsonValidation={jsonValidation}
        jsonError={jsonError}
        onJsonTitleChange={onJsonTitleChange}
        onJsonContentChange={onJsonContentChange}
        onClearJson={onClearJson}
        canSubmitFile={canSubmitFile}
        canSubmitText={canSubmitText}
        canSubmitJson={canSubmitJson}
        isSubmitting={isSubmitting}
        submitError={submitError}
        onSubmit={onSubmitTraining}
      />
    </>
  );
}
