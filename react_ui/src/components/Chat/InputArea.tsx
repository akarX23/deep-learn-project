import { uiClasses } from "../../styles/uiClasses";

interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}

export function InputArea({ value, onChange, disabled }: InputAreaProps): JSX.Element {
  return (
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
  );
}
