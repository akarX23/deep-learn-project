import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type { StreamCompletionPayload, StreamTokensEventBody } from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";
// import { theme } from "../../styles/theme";
import { LoadingIndicator } from "./LoadingIndicator";

interface StreamResponseBoxProps {
  sid: string | null;
  messageId: string;
  isActive: boolean;
  initialContent: string;
  initialTokensUsed?: number;
  progressPlaceholder: string;
  onDone: (payload: StreamCompletionPayload) => void;
}

export function StreamResponseBox({
  sid,
  messageId,
  isActive,
  initialContent,
  initialTokensUsed,
  progressPlaceholder,
  onDone
}: StreamResponseBoxProps): JSX.Element {
  const [markdownContent, setMarkdownContent] = useState(initialContent);
  const [isStreaming, setIsStreaming] = useState(isActive);
  const [tokensUsed, setTokensUsed] = useState<number | null>(initialTokensUsed ?? null);
  const previousFieldRef = useRef<string | null>(null);

  useEffect(() => {
    setMarkdownContent(initialContent);
    setIsStreaming(isActive);
    setTokensUsed(initialTokensUsed ?? null);
    previousFieldRef.current = null;
  }, [initialContent, initialTokensUsed, isActive, messageId]);

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

        const field = typeof payload.data.field === "string" ? payload.data.field.trim() : "";
        let sectionHeading = "";
        if (field && field !== previousFieldRef.current) {
          sectionHeading = `\n\n## ${field.charAt(0).toUpperCase() + field.slice(1)}\n\n`;
          previousFieldRef.current = field;
        }

        if (payload.data.done === true) {
          const trailingToken = typeof payload.data.token === "string" ? payload.data.token : "";
          const completionAppend = `${sectionHeading}${trailingToken}`;
          const finalContent = completionAppend ? markdownContent + completionAppend : markdownContent;
          if (completionAppend) {
            setMarkdownContent(finalContent);
          }

          const completionTokensUsed =
            typeof payload.data.tokens_used === "number" ? payload.data.tokens_used : undefined;
          setIsStreaming(false);
          setTokensUsed(completionTokensUsed ?? null);
          onDone({
            messageId,
            fullContent: finalContent,
            tokens_used: completionTokensUsed
          });
          return;
        }

        const token = typeof payload.data.token === "string" ? payload.data.token : "";
        const tokenAppend = `${sectionHeading}${token}`;
        if (tokenAppend) {
          setMarkdownContent((prev) => prev + tokenAppend);
        }
      },
      [isActive, markdownContent, messageId, onDone, sid]
    )
  );

  return (
    <div className={uiClasses.chat.markdownBox}>
      {markdownContent ? (
        <div className="markdown-body">
            <ReactMarkdown>{markdownContent}</ReactMarkdown>
        </div>
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