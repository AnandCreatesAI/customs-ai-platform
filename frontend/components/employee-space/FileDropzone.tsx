'use client';

import { UploadCloud } from 'lucide-react';
import { useState } from 'react';

import {
  MAX_TRAINING_FILE_SIZE_MB,
  TRAINING_ALLOWED_EXTENSIONS,
} from '@/lib/employee-space/training-files';

const FILE_INPUT_ACCEPT = TRAINING_ALLOWED_EXTENSIONS.map((ext) => `.${ext}`).join(',');

type FileDropzoneProps = {
  onFilesSelected: (files: FileList | File[]) => void;
  errorMessage?: string | null;
  disabled?: boolean;
  disabledHint?: string;
};

export function FileDropzone({
  onFilesSelected,
  errorMessage,
  disabled = false,
  disabledHint,
}: FileDropzoneProps) {
  const [dragActive, setDragActive] = useState(false);

  function handleFiles(fileList: FileList | File[] | null) {
    const files = fileList ? Array.from(fileList) : [];
    if (disabled || files.length === 0) {
      return;
    }
    onFilesSelected(files);
  }

  return (
    <div className="space-y-2">
      <div
        data-testid="file-dropzone"
        onClick={(event) => event.stopPropagation()}
        onMouseDown={(event) => event.stopPropagation()}
        onDragEnter={(event) => {
          event.preventDefault();
          event.stopPropagation();
          if (!disabled) {
            setDragActive(true);
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          event.stopPropagation();
          if (!disabled) {
            event.dataTransfer.dropEffect = 'copy';
            setDragActive(true);
          }
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setDragActive(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setDragActive(false);
          handleFiles(
            event.dataTransfer.files ? Array.from(event.dataTransfer.files) : [],
          );
        }}
        className={`rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
          disabled
            ? 'cursor-not-allowed border-zinc-200 bg-zinc-100 opacity-70'
            : dragActive
              ? 'border-indigo-400 bg-indigo-50/50'
              : 'border-zinc-200 bg-zinc-50/80 hover:border-zinc-300'
        }`}
      >
        <UploadCloud className="mx-auto h-10 w-10 text-zinc-400" aria-hidden />
        <p className="mt-3 text-sm font-medium text-zinc-800">Drag and drop files here</p>
        <p className="mt-1 text-xs text-zinc-500">
          {TRAINING_ALLOWED_EXTENSIONS.map((ext) => ext.toUpperCase()).join(', ')} · Maximum file
          size: {MAX_TRAINING_FILE_SIZE_MB} MB per file
        </p>
        {disabled && disabledHint ? (
          <p className="mt-2 text-xs text-amber-800" data-testid="file-dropzone-disabled-hint">
            {disabledHint}
          </p>
        ) : null}

        {disabled ? (
          <span
            data-testid="file-dropzone-browse"
            className="mt-4 inline-block cursor-not-allowed rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-500 opacity-60"
          >
            Browse files
          </span>
        ) : (
          <label
            data-testid="file-dropzone-browse"
            className="mt-4 inline-block cursor-pointer rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-50 focus-within:outline-none focus-within:ring-2 focus-within:ring-indigo-300"
          >
            Browse files
            <input
              type="file"
              multiple
              accept={FILE_INPUT_ACCEPT}
              data-testid="file-dropzone-input"
              className="sr-only"
              onChange={(event) => {
                const picked =
                  event.target.files && event.target.files.length > 0
                    ? Array.from(event.target.files)
                    : [];
                event.target.value = '';
                handleFiles(picked);
              }}
            />
          </label>
        )}
      </div>
      {errorMessage ? (
        <p role="alert" data-testid="file-dropzone-error" className="text-sm text-red-600">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
