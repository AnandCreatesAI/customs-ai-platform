'use client';

import { useCallback, useEffect } from 'react';

import { FileUploadSection } from '@/components/employee-space/FileUploadSection';
import { JsonTrainingEditor } from '@/components/employee-space/JsonTrainingEditor';
import { TextTrainingEditor } from '@/components/employee-space/TextTrainingEditor';
import { TrainingModalShell } from '@/components/employee-space/TrainingModalShell';
import { getBusinessModelLabel, type BusinessModelKey } from '@/lib/dashboard/business-models';
import type { JsonValidationResult } from '@/lib/employee-space/json-training';
import { platformPrimaryButtonClassName } from '@/lib/platform-primary';
import type { TrainingFileMetadata, TrainingSourceType } from '@/lib/employee-space/types';

export type TrainModelModalStep = null | 'menu' | TrainingSourceType;

const MENU_OPTIONS: {
  step: TrainingSourceType;
  label: string;
  description: string;
}[] = [
  {
    step: 'file',
    label: 'File Training',
    description: 'Upload PDF, DOC, DOCX, XLS, XLSX, CSV, TXT or JSON files.',
  },
  {
    step: 'text',
    label: 'Text Training',
    description: 'Enter a training title and text content.',
  },
  {
    step: 'json',
    label: 'JSON Training',
    description: 'Enter a training title and JSON content.',
  },
];

type TrainModelModalsProps = {
  selectedModelKey: BusinessModelKey | null;
  step: TrainModelModalStep;
  onStepChange: (step: TrainModelModalStep) => void;
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
  onSubmit: (source: TrainingSourceType) => void;
};

export function TrainModelModals({
  selectedModelKey,
  step,
  onStepChange,
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
  onSubmit,
}: TrainModelModalsProps) {
  const modelLabel = selectedModelKey ? getBusinessModelLabel(selectedModelKey) : null;

  const closeAll = useCallback(() => onStepChange(null), [onStepChange]);

  useEffect(() => {
    if (!step) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        closeAll();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [closeAll, step]);

  return (
    <>
      <TrainingModalShell
        open={step === 'menu'}
        title="Train Model"
        modelLabel={modelLabel}
        onClose={closeAll}
        onBack={closeAll}
        backLabel="Back to workspace"
        testId="train-model-menu-modal"
      >
        <p className="text-sm text-zinc-600">
          Choose how you want to add training data for the selected business model.
        </p>
        <ul className="mt-4 grid gap-3">
          {MENU_OPTIONS.map((option) => (
            <li key={option.step}>
              <button
                type="button"
                data-testid={`train-model-option-${option.step}`}
                disabled={!selectedModelKey}
                onClick={() => onStepChange(option.step)}
                className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-left transition hover:border-indigo-300 hover:bg-indigo-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span className="block text-sm font-semibold text-zinc-900">{option.label}</span>
                <span className="mt-1 block text-xs text-zinc-600">{option.description}</span>
              </button>
            </li>
          ))}
        </ul>
        {!selectedModelKey ? (
          <p className="mt-3 text-xs text-amber-800" role="status">
            Select User, eBooks, Employee or HS Code on the left before training.
          </p>
        ) : null}
      </TrainingModalShell>

      <TrainingModalShell
        open={step === 'file'}
        title="File Training"
        modelLabel={modelLabel}
        onClose={closeAll}
        onBack={() => onStepChange('menu')}
        testId="train-model-file-modal"
        footer={
          <div className="flex flex-col gap-2">
            <button
              type="button"
              data-testid="train-model-file-submit"
              disabled={!canSubmitFile || isSubmitting || !selectedModelKey}
              onClick={() => onSubmit('file')}
              className={`cursor-pointer px-5 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-300 disabled:text-zinc-600 ${platformPrimaryButtonClassName}`}
            >
              {isSubmitting ? 'Uploading…' : 'Upload files'}
            </button>
            {submitError ? (
              <p role="alert" className="text-sm text-red-600">
                {submitError}
              </p>
            ) : null}
          </div>
        }
      >
        <FileUploadSection
          businessModelKey={selectedModelKey}
          fileTitle={fileTitle}
          onFileTitleChange={onFileTitleChange}
          fileTitleError={fileTitleError}
          selectedFiles={selectedFiles}
          fileError={fileError}
          dropzoneDisabled={!selectedModelKey}
          onFilesSelected={onFilesSelected}
          onRemoveFile={onRemoveFile}
        />
      </TrainingModalShell>

      <TrainingModalShell
        open={step === 'text'}
        title="Text Training"
        modelLabel={modelLabel}
        onClose={closeAll}
        onBack={() => onStepChange('menu')}
        testId="train-model-text-modal"
        footer={
          <div className="flex flex-col gap-2">
            <button
              type="button"
              data-testid="train-model-text-submit"
              disabled={!canSubmitText || isSubmitting || !selectedModelKey}
              onClick={() => onSubmit('text')}
              className={`cursor-pointer px-5 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-300 disabled:text-zinc-600 ${platformPrimaryButtonClassName}`}
            >
              {isSubmitting ? 'Saving…' : 'Save text'}
            </button>
            {textError ? (
              <p role="alert" className="text-sm text-red-600">
                {textError}
              </p>
            ) : null}
            {submitError ? (
              <p role="alert" className="text-sm text-red-600">
                {submitError}
              </p>
            ) : null}
          </div>
        }
      >
        <TextTrainingEditor
          title={textTitle}
          content={textContent}
          onTitleChange={onTextTitleChange}
          onContentChange={onTextContentChange}
          onClear={onClearText}
          errorMessage={null}
        />
      </TrainingModalShell>

      <TrainingModalShell
        open={step === 'json'}
        title="JSON Training"
        modelLabel={modelLabel}
        onClose={closeAll}
        onBack={() => onStepChange('menu')}
        testId="train-model-json-modal"
        footer={
          <div className="flex flex-col gap-2">
            <button
              type="button"
              data-testid="train-model-json-submit"
              disabled={!canSubmitJson || isSubmitting || !selectedModelKey}
              onClick={() => onSubmit('json')}
              className={`cursor-pointer px-5 disabled:cursor-not-allowed disabled:border-zinc-300 disabled:bg-zinc-300 disabled:text-zinc-600 ${platformPrimaryButtonClassName}`}
            >
              {isSubmitting ? 'Saving…' : 'Save JSON'}
            </button>
            {jsonError ? (
              <p role="alert" className="text-sm text-red-600">
                {jsonError}
              </p>
            ) : null}
            {submitError ? (
              <p role="alert" className="text-sm text-red-600">
                {submitError}
              </p>
            ) : null}
          </div>
        }
      >
        <JsonTrainingEditor
          title={jsonTitle}
          content={jsonContent}
          modelLabel={modelLabel}
          onTitleChange={onJsonTitleChange}
          onContentChange={onJsonContentChange}
          onClear={onClearJson}
          validation={jsonValidation}
        />
      </TrainingModalShell>
    </>
  );
}
