import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type { StreamTokensEventBody } from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";
import { LoadingIndicator } from "./LoadingIndicator";

interface StreamResponseBoxProps {
  sid: string | null;
  messageId: string;
  isActive: boolean;
  initialContent: string;
  progressPlaceholder: string;
  onDone: () => void;
}

export function StreamResponseBox({
  sid,
  messageId,
  isActive,
  initialContent,
  progressPlaceholder,
  onDone
}: StreamResponseBoxProps): JSX.Element {
  const [markdownContent, setMarkdownContent] = useState(initialContent);
  const [isStreaming, setIsStreaming] = useState(isActive);
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);

  useEffect(() => {
    setMarkdownContent(initialContent);
    setIsStreaming(isActive);
    setTokensUsed(null);
  }, [initialContent, isActive, messageId]);

  useSocketEvent<StreamTokensEventBody>(
    WebSocketEvents.STREAM_TOKENS_SKT,
    useCallback(
      (payload) => {
        if (!isActive) {
          return;
        }
        if (!sid || payload.sid !== sid) {
          return;
        }
        if (payload.from_service !== "teaching-agent") {
          return;
        }

        if (payload.data.done === true) {
          setIsStreaming(false);
          setTokensUsed(typeof payload.data.tokens_used === "number" ? payload.data.tokens_used : null);
          onDone();
          return;
        }

        const token = typeof payload.data.token === "string" ? payload.data.token : "";
        if (token) {
          setMarkdownContent((prev) => prev + token);
        }
      },
      [isActive, onDone, sid]
    )
  );

  return (
    <div className={uiClasses.chat.markdownBox}>
      {markdownContent ? (
        <ReactMarkdown>{markdownContent}</ReactMarkdown>
      ) : (
        <span className="text-slate-400">{isStreaming ? "Preparing response..." : "No response yet."}</span>
      )}

      {isStreaming && <LoadingIndicator placeholderText={progressPlaceholder} />}
      {!isStreaming && tokensUsed !== null && (
        <p className={uiClasses.loading.usage}>Tokens used: {tokensUsed}</p>
      )}
    </div>
  );
}