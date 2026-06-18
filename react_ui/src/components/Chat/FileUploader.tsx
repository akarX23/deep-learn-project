import { uiClasses } from "../../styles/uiClasses";

interface FileUploaderProps {
  files: File[];
  errors: string[];
  onAdd: (files: FileList | null) => void;
  onRemove: (index: number) => void;
  disabled: boolean;
}

export function FileUploader({ files, errors, onAdd, onRemove, disabled }: FileUploaderProps): JSX.Element {
  return (
    <div className={uiClasses.uploader.shell}>
      <label htmlFor="pdf-files" className={uiClasses.uploader.label}>
        Upload PDFs (max 3, 20 MB each)
      </label>
      <label htmlFor="pdf-files" className={uiClasses.uploader.picker} aria-disabled={disabled}>
        Choose files
      </label>
      <input
        id="pdf-files"
        className={uiClasses.uploader.hiddenInput}
        type="file"
        accept="application/pdf"
        multiple
        onChange={(event) => onAdd(event.target.files)}
        disabled={disabled}
        aria-label="Upload PDF files"
      />

      {files.length > 0 && (
        <ul className={uiClasses.uploader.list}>
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`} className={uiClasses.uploader.fileItem}>
              <span>
                {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
              </span>
              <button
                type="button"
                onClick={() => onRemove(index)}
                disabled={disabled}
                className={uiClasses.uploader.remove}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {errors.length > 0 && (
        <div role="alert" aria-live="polite" className={uiClasses.uploader.errorBox}>
          {errors.map((error) => (
            <div key={error}>{error}</div>
          ))}
        </div>
      )}
    </div>
  );
}
