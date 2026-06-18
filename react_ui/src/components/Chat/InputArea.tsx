interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}

export function InputArea({ value, onChange, onSubmit, disabled }: InputAreaProps): JSX.Element {
  return (
    <div>
      <label htmlFor="chat-input" style={{ display: "block", marginBottom: 6 }}>
        Ask AI Tutor
      </label>
      <textarea
        id="chat-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        style={{ width: "100%", borderRadius: 8, padding: 8 }}
        disabled={disabled}
        aria-label="Chat prompt input"
      />
      <button
        type="button"
        onClick={onSubmit}
        disabled={disabled || value.trim().length === 0}
        aria-disabled={disabled || value.trim().length === 0}
        style={{ marginTop: 8, padding: "8px 12px", borderRadius: 8 }}
      >
        Send
      </button>
    </div>
  );
}
