import { uiClasses } from "../../styles/uiClasses";

interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}

export function InputArea({ value, onChange, onSubmit, disabled }: InputAreaProps): JSX.Element {
  return (
    <div>
      <label htmlFor="chat-input" className={uiClasses.input.label}>
        Ask AI Tutor
      </label>
      <textarea
        id="chat-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        className={uiClasses.input.textarea}
        disabled={disabled}
        aria-label="Chat prompt input"
        placeholder="Ask a question about your topic..."
      />
      <button
        type="button"
        onClick={onSubmit}
        disabled={disabled || value.trim().length === 0}
        aria-disabled={disabled || value.trim().length === 0}
        className={uiClasses.input.submit}
      >
        Send
      </button>
    </div>
  );
}
