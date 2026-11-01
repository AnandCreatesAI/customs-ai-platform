'use client';

import { UploadCloud } from 'lucide-react';
import { useId, useRef, useState } from 'react';

import {
  MAX_TRAINING_FILE_SIZE_MB,
  TRAINING_ALLOWED_EXTENSIONS,
} from '@/lib/employee-space/training-files';

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
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  function handleFiles(fileList: FileList | null) {
    if (disabled || !fileList || fileList.length === 0) {
      return;
    }
    onFilesSelected(fileList);
  }

  return (
    <div className="space-y-2">
      <div
        data-testid="file-dropzone"
        onDragEnter={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragActive(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          handleFiles(event.dataTransfer.files);
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
        <button
          type="button"
          data-testid="file-dropzone-browse"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="mt-4 cursor-pointer rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
        >
          Browse files
        </button>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          multiple
          disabled={disabled}
          data-testid="file-dropzone-input"
          className="sr-only"
          onChange={(event) => {
            handleFiles(event.target.files);
            event.target.value = '';
          }}
        />
      </div>
      {errorMessage ? (
        <p role="alert" data-testid="file-dropzone-error" className="text-sm text-red-600">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
