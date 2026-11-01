'use client';

import { FileDropzone } from '@/components/employee-space/FileDropzone';
import { SelectedFileList } from '@/components/employee-space/SelectedFileList';
import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import type { TrainingFileMetadata } from '@/lib/employee-space/types';

type FileUploadSectionProps = {
  businessModelKey?: BusinessModelKey | null;
  fileTitle: string;
  onFileTitleChange: (value: string) => void;
  fileTitleError: string | null;
  selectedFiles: TrainingFileMetadata[];
  fileError: string | null;
  dropzoneDisabled: boolean;
  onFilesSelected: (files: FileList | File[]) => void;
  onRemoveFile: (id: string) => void;
};

export function FileUploadSection({
  businessModelKey = null,
  fileTitle,
  onFileTitleChange,
  fileTitleError,
  selectedFiles,
  fileError,
  dropzoneDisabled,
  onFilesSelected,
  onRemoveFile,
}: FileUploadSectionProps) {
  const filesForModel =
    businessModelKey === null
      ? selectedFiles
      : selectedFiles.filter((file) => file.modelKey === businessModelKey);
  const showTitleRequired = filesForModel.length > 0 && fileTitle.trim().length === 0;

  return (
    <div className="space-y-4" data-testid="file-upload-section">
      <div className="space-y-1.5">
        <label htmlFor="training-file-title" className="text-sm font-medium text-zinc-800">
          File Title <span className="text-red-600">*</span>
        </label>
        <input
          id="training-file-title"
          data-testid="training-file-title"
          value={fileTitle}
          onChange={(event) => onFileTitleChange(event.target.value)}
          placeholder="Enter a title for these documents"
          className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-900 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />
        {fileTitleError ? (
          <p role="alert" data-testid="file-title-error" className="text-sm text-red-600">
            {fileTitleError}
          </p>
        ) : showTitleRequired ? (
          <p className="text-sm text-amber-800" data-testid="file-title-required-hint">
            Enter a file title before starting training.
          </p>
        ) : null}
      </div>

      <FileDropzone
        onFilesSelected={onFilesSelected}
        errorMessage={fileError}
        disabled={dropzoneDisabled}
        disabledHint="Select a model before uploading files."
      />

      <SelectedFileList
        files={filesForModel}
        groupTitle={fileTitle.trim() || null}
        onRemove={onRemoveFile}
      />
    </div>
  );
}
