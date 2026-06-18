interface FileUploaderProps {
  files: File[];
  errors: string[];
  onAdd: (files: FileList | null) => void;
  onRemove: (index: number) => void;
  disabled: boolean;
}

export function FileUploader({ files, errors, onAdd, onRemove, disabled }: FileUploaderProps): JSX.Element {
  return (
    <div style={{ marginBottom: 12 }}>
      <label htmlFor="pdf-files" style={{ display: "block", marginBottom: 6 }}>
        Upload PDFs (max 3, 20 MB each)
      </label>
      <input
        id="pdf-files"
        type="file"
        accept="application/pdf"
        multiple
        onChange={(event) => onAdd(event.target.files)}
        disabled={disabled}
        aria-label="Upload PDF files"
      />

      {files.length > 0 && (
        <ul style={{ marginTop: 8, paddingLeft: 18 }}>
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`}>
              {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
              <button
                type="button"
                onClick={() => onRemove(index)}
                disabled={disabled}
                style={{ marginLeft: 8 }}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {errors.length > 0 && (
        <div role="alert" aria-live="polite" style={{ color: "#b91c1c", marginTop: 8 }}>
          {errors.map((error) => (
            <div key={error}>{error}</div>
          ))}
        </div>
      )}
    </div>
  );
}
