import { useCallback, useEffect, useRef, useState } from "react";
import { useBatchedTokens } from "../../hooks/useBatchedTokens";
import { usePdfValidator } from "../../hooks/usePdfValidator";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type { ChatMessage, ClarifyUserLevelEvent, StreamTokensEventBody } from "../../schemas";
import { WebSocketEvents } from "../../schemas";
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const { files, errors, addFiles, removeFile, clearFiles } = usePdfValidator();
  const { streamedText, addToken, reset } = useBatchedTokens(100);
  const stopStreamingTimerRef = useRef<number | null>(null);

  useSocketEvent<StreamTokensEventBody>(WebSocketEvents.STREAM_TOKENS_SKT, useCallback((payload) => {
    if (!sid || payload.sid !== sid) {
      return;
    }
    if (payload.from_service !== "teaching-agent") {
      return;
    }

    const token = typeof payload.data.token === "string" ? payload.data.token : "";
    if (!token) {
      return;
    }

    addToken(token);

    if (stopStreamingTimerRef.current !== null) {
      window.clearTimeout(stopStreamingTimerRef.current);
    }
    stopStreamingTimerRef.current = window.setTimeout(() => {
      setIsSubmitting(false);
      setMessages((prev) => {
        if (prev.length === 0) {
          return prev;
        }
        const next = [...prev];
        const last = next[next.length - 1];
        if (last.role === "assistant") {
          next[next.length - 1] = { ...last, isStreaming: false };
        }
        return next;
      });
    }, 800);
  }, [addToken, sid]));

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

  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 0) {
        return prev;
      }
      const next = [...prev];
      const last = next[next.length - 1];
      if (last.role === "assistant" && last.isStreaming) {
        next[next.length - 1] = { ...last, content: streamedText };
      }
      return next;
    });
  }, [streamedText]);

  const handleSubmit = async (): Promise<void> => {
    if (!sid || isSubmitting || inputText.trim().length === 0) {
      return;
    }

    const prompt = inputText.trim();
    setRequestError(null);
    setIsSubmitting(true);
    reset();

    setMessages((prev) => [
      ...prev,
      { id: uuid(), role: "user", content: prompt, isStreaming: false },
      { id: uuid(), role: "assistant", content: "", isStreaming: true }
    ]);

    setInputText("");

    try {
      await onSubmitRequest(prompt, files);
      clearFiles();
    } catch (error) {
    console.log(`Error on API call: `, error)
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
      <h2 style={{ marginTop: 0 }}>AI Tutor</h2>
      <p style={{ color: "#4b5563" }}>Ask a question and optionally upload PDF study material.</p>

      <MessageList messages={messages} />

      <FileUploader
        files={files}
        errors={errors}
        onAdd={addFiles}
        onRemove={removeFile}
        disabled={isSubmitting}
      />

      <InputArea value={inputText} onChange={setInputText} onSubmit={handleSubmit} disabled={isSubmitting} />

      {!sid && <p style={{ color: "#b91c1c" }}>Connecting to backend...</p>}
      {requestError && <p style={{ color: "#b91c1c" }}>{requestError}</p>}
    </section>
  );
}
