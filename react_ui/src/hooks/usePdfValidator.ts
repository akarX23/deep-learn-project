import { useState } from "react";

const MAX_FILES = 3;
const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export function usePdfValidator(): {
  files: File[];
  errors: string[];
  addFiles: (fileList: FileList | null) => void;
  removeFile: (index: number) => void;
  clearFiles: () => void;
} {
  const [files, setFiles] = useState<File[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  const addFiles = (fileList: FileList | null): void => {
    if (!fileList) {
      return;
    }

    const incoming = Array.from(fileList);
    const nextErrors: string[] = [];

    if (files.length + incoming.length > MAX_FILES) {
      nextErrors.push(`You can upload at most ${MAX_FILES} PDF files.`);
    }

    incoming.forEach((file) => {
      if (file.type !== "application/pdf") {
        nextErrors.push(`${file.name}: only PDF files are allowed.`);
      }
      if (file.size > MAX_FILE_SIZE_BYTES) {
        nextErrors.push(`${file.name}: exceeds ${MAX_FILE_SIZE_MB} MB limit.`);
      }
    });

    if (nextErrors.length > 0) {
      setErrors(nextErrors);
      return;
    }

    setErrors([]);
    setFiles((prev) => [...prev, ...incoming].slice(0, MAX_FILES));
  };

  const removeFile = (index: number): void => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const clearFiles = (): void => {
    setFiles([]);
    setErrors([]);
  };

  return { files, errors, addFiles, removeFile, clearFiles };
}
