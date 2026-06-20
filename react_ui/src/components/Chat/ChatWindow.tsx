import { useCallback, useEffect, useState } from "react";
import { usePdfValidator } from "../../hooks/usePdfValidator";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type {
  ChatMessage,
  ClarifyUserLevelEvent,
  StreamCompletionPayload,
  StreamProgressUpdateEventBody
} from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";
import { FileUploader } from "./FileUploader";
import { InputArea } from "./InputArea";
import { MessageList } from "./MessageList";

interface ChatWindowProps {
  sid: string | null;
  onSubmitRequest: (prompt: string, files: File[]) => Promise<void>;
  onContextChange?: (context: ChatWindowContext) => void;
}

export interface ChatWindowContext {
  messages: ChatMessage[];
  activeStreamMessageId: string | null;
  inputText: string;
  isSubmitting: boolean;
  requestError: string | null;
  files: Array<{ name: string; sizeBytes: number }>;
  errors: string[];
}

function uuid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ChatWindow({ sid, onSubmitRequest, onContextChange }: ChatWindowProps): JSX.Element {
  const progressPlaceholder = "Backend progress events will appear here.";
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeStreamMessageId, setActiveStreamMessageId] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const { files, errors, addFiles, removeFile, clearFiles } = usePdfValidator();

  useEffect(() => {
    if (!onContextChange) {
      return;
    }

    onContextChange({
      messages,
      activeStreamMessageId,
      inputText,
      isSubmitting,
      requestError,
      files: files.map((file) => ({ name: file.name, sizeBytes: file.size })),
      errors
    });
  }, [
    activeStreamMessageId,
    errors,
    files,
    inputText,
    isSubmitting,
    messages,
    onContextChange,
    requestError
  ]);

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

  useSocketEvent<StreamProgressUpdateEventBody>(
    WebSocketEvents.STREAM_PROGRESS_UPDATE_SKT,
    useCallback(
      (payload) => {
        if (!sid || payload.sid !== sid || payload.for_page !== "chat") {
          return;
        }

        console.log("Chat", payload.update);
      },
      [sid]
    )
  );

  const handleAssistantStreamDone = useCallback((payload: StreamCompletionPayload): void => {
    setIsSubmitting(false);
    setActiveStreamMessageId((prev) => (prev === payload.messageId ? null : prev));
    setMessages((prev) =>
      prev.map((message) =>
        message.id === payload.messageId
          ? {
              ...message,
              content: payload.fullContent,
              isStreaming: false,
              tokens_used: payload.tokens_used,
              model: payload.model
            }
          : message
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
      <MessageList
        messages={messages}
        sid={sid}
        activeStreamMessageId={activeStreamMessageId}
        progressPlaceholder={progressPlaceholder}
        onAssistantStreamDone={handleAssistantStreamDone}
      />

      <div className="mt-4">
        <InputArea value={inputText} onChange={setInputText} disabled={isSubmitting} />

        <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || inputText.trim().length === 0}
            aria-disabled={isSubmitting || inputText.trim().length === 0}
            className={uiClasses.input.submit}
          >
            Send
          </button>

          <div className="md:shrink-0">
            <FileUploader
              files={files}
              errors={errors}
              onAdd={addFiles}
              onRemove={removeFile}
              disabled={isSubmitting}
            />
          </div>
        </div>
      </div>

      {!sid && <p className={uiClasses.chat.errorText}>Connecting to backend...</p>}
      {requestError && <p className={uiClasses.chat.errorText}>{requestError}</p>}
    </section>
  );
}
