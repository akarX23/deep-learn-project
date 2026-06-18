import { useCallback, useState } from "react";
import { usePdfValidator } from "../../hooks/usePdfValidator";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type { ChatMessage, ClarifyUserLevelEvent } from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";
import { FileUploader } from "./FileUploader";
import { InputArea } from "./InputArea";
import { MessageList } from "./MessageList";

interface ChatWindowProps {
  sid: string | null;
  onSubmitRequest: (prompt: string, files: File[]) => Promise<void>;
}

function uuid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ChatWindow({ sid, onSubmitRequest }: ChatWindowProps): JSX.Element {
  const progressPlaceholder = "Backend progress events will appear here.";
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeStreamMessageId, setActiveStreamMessageId] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const { files, errors, addFiles, removeFile, clearFiles } = usePdfValidator();

  useSocketEvent<ClarifyUserLevelEvent>(WebSocketEvents.CLARIFY_USER_LEVEL_SKT, useCallback((payload) => {
    if (!sid || payload.sid !== sid) {
      return;
    }

    const content = payload.reason?.trim() || "Please clarify your learning level so I can continue.";
    setMessages((prev) => [
      ...prev,
      { id: uuid(), role: "assistant", content, isStreaming: false, info: true }
    ]);
  }, [sid]));

  const handleAssistantStreamDone = useCallback((messageId: string): void => {
    setIsSubmitting(false);
    setActiveStreamMessageId((prev) => (prev === messageId ? null : prev));
    setMessages((prev) =>
      prev.map((message) =>
        message.id === messageId ? { ...message, isStreaming: false } : message
      )
    );
  }, []);

  const handleSubmit = async (): Promise<void> => {
    if (!sid || isSubmitting || inputText.trim().length === 0) {
      return;
    }

    const prompt = inputText.trim();
    setRequestError(null);
    setIsSubmitting(true);
    const assistantMessageId = uuid();

    setMessages((prev) => [
      ...prev,
      {
        id: uuid(),
        role: "user",
        content: prompt,
        isStreaming: false,
        attachments: files.map((file) => ({ name: file.name, sizeBytes: file.size }))
      },
      { id: assistantMessageId, role: "assistant", content: "", isStreaming: true }
    ]);
    setActiveStreamMessageId(assistantMessageId);

    setInputText("");

    try {
      await onSubmitRequest(prompt, files);
      clearFiles();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to submit request";
      setIsSubmitting(false);
      setMessages((prev) => [
        ...prev,
        { id: uuid(), role: "assistant", content: `Error: ${message}`, isStreaming: false, info: true }
      ]);
      setRequestError(message);
    }
  };

  return (
    <section>
      <h2 className={uiClasses.chat.heading}>Chat</h2>
      <p className={uiClasses.chat.subheading}>Ask a question and optionally upload PDF study material.</p>

      <MessageList
        messages={messages}
        sid={sid}
        activeStreamMessageId={activeStreamMessageId}
        progressPlaceholder={progressPlaceholder}
        onAssistantStreamDone={handleAssistantStreamDone}
      />

      <FileUploader
        files={files}
        errors={errors}
        onAdd={addFiles}
        onRemove={removeFile}
        disabled={isSubmitting}
      />

      <InputArea value={inputText} onChange={setInputText} onSubmit={handleSubmit} disabled={isSubmitting} />

      {!sid && <p className={uiClasses.chat.errorText}>Connecting to backend...</p>}
      {requestError && <p className={uiClasses.chat.errorText}>{requestError}</p>}
    </section>
  );
}
