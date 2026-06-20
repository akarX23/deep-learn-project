import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { rehypeMermaid, MermaidBlock } from 'react-markdown-mermaid';
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
  initialModel?: string;
  progressPlaceholder: string;
  onDone: (payload: StreamCompletionPayload) => void;
}

export function StreamResponseBox({
  sid,
  messageId,
  isActive,
  initialContent,
  initialTokensUsed,
  initialModel,
  progressPlaceholder,
  onDone
}: StreamResponseBoxProps): JSX.Element {
  const mermaidComponents = { MermaidBlock } as unknown as Components;
  const [markdownContent, setMarkdownContent] = useState(initialContent);
  const [isStreaming, setIsStreaming] = useState(isActive);
  const [tokensUsed, setTokensUsed] = useState<number | null>(initialTokensUsed ?? null);
  const [model, setModel] = useState<string | null>(initialModel ?? null);
  const [revealPulse, setRevealPulse] = useState(false);
  const previousFieldRef = useRef<string | null>(null);
  const revealTimerRef = useRef<number | null>(null);
  const flushTimerRef = useRef<number | null>(null);
  const pendingBufferRef = useRef<string>("");
  const currentContentRef = useRef<string>(initialContent);
  const isDiagramField = (value: string): boolean => value.toLowerCase() === "diagram";

  const _STREAM_FLUSH_INTERVAL_MS = 22;
  const _STREAM_FLUSH_CHARS_PER_TICK = 5;

  const appendToContent = useCallback((chunk: string): void => {
    if (!chunk) {
      return;
    }
    setMarkdownContent((prev) => {
      const next = prev + chunk;
      currentContentRef.current = next;
      return next;
    });
  }, []);

  const stopFlushLoop = useCallback((): void => {
    if (flushTimerRef.current !== null) {
      window.clearInterval(flushTimerRef.current);
      flushTimerRef.current = null;
    }
  }, []);

  const startFlushLoop = useCallback((): void => {
    if (flushTimerRef.current !== null) {
      return;
    }

    flushTimerRef.current = window.setInterval(() => {
      if (!pendingBufferRef.current) {
        stopFlushLoop();
        return;
      }

      const nextChunk = pendingBufferRef.current.slice(0, _STREAM_FLUSH_CHARS_PER_TICK);
      pendingBufferRef.current = pendingBufferRef.current.slice(_STREAM_FLUSH_CHARS_PER_TICK);
      appendToContent(nextChunk);
    }, _STREAM_FLUSH_INTERVAL_MS);
  }, [appendToContent, stopFlushLoop]);

  const enqueueStreamChunk = useCallback((chunk: string): void => {
    if (!chunk) {
      return;
    }
    pendingBufferRef.current += chunk;
    startFlushLoop();
  }, [startFlushLoop]);

  const flushAllPending = useCallback((): void => {
    if (!pendingBufferRef.current) {
      return;
    }
    const pending = pendingBufferRef.current;
    pendingBufferRef.current = "";
    stopFlushLoop();
    appendToContent(pending);
  }, [appendToContent, stopFlushLoop]);

  useEffect(() => {
    setMarkdownContent(initialContent);
    setIsStreaming(isActive);
    setTokensUsed(initialTokensUsed ?? null);
    setModel(initialModel ?? null);
    setRevealPulse(false);
    currentContentRef.current = initialContent;
    pendingBufferRef.current = "";
    stopFlushLoop();
    previousFieldRef.current = null;
  }, [initialContent, initialTokensUsed, initialModel, isActive, messageId, stopFlushLoop]);

  useEffect(() => {
    return () => {
      if (revealTimerRef.current !== null) {
        window.clearTimeout(revealTimerRef.current);
      }
      stopFlushLoop();
    };
  }, [stopFlushLoop]);

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
          flushAllPending();
          const completionTokensUsed =
            typeof payload.data.tokens_used === "number" ? payload.data.tokens_used : undefined;
          const completionModel =
            typeof payload.data.model === "string" && payload.data.model.trim().length > 0
              ? payload.data.model.trim()
              : undefined;
          setIsStreaming(false);
          setTokensUsed(completionTokensUsed ?? null);
          setModel(completionModel ?? null);
          onDone({
            messageId,
            fullContent: currentContentRef.current,
            tokens_used: completionTokensUsed,
            model: completionModel
          });
          return;
        }

        let token = typeof payload.data.token === "string" ? payload.data.token : "";

        if (isDiagramField(field)) {
          token = `\`\`\`mermaid\n${token}\n\`\`\``;
        }

        const tokenAppend = `${sectionHeading}${token}`;
        if (tokenAppend) {
          setRevealPulse(true);
          if (revealTimerRef.current !== null) {
            window.clearTimeout(revealTimerRef.current);
          }
          revealTimerRef.current = window.setTimeout(() => {
            setRevealPulse(false);
          }, 170);
          enqueueStreamChunk(tokenAppend);
        }
      },
      [enqueueStreamChunk, flushAllPending, isActive, messageId, onDone, sid]
    )
  );

  return (
    <div className={uiClasses.chat.markdownBox}>
      {markdownContent ? (
        <div
          className={`markdown-body ${uiClasses.chat.streamRevealBase} ${
            revealPulse ? uiClasses.chat.streamRevealActive : uiClasses.chat.streamRevealIdle
          }`}
        >
            <ReactMarkdown
              rehypePlugins={[
                [
                  rehypeMermaid,
                  {
                    mermaidConfig: {
                      theme: 'default',
                      flowchart: { useMaxWidth: true },
                    },
                  },
                ],
              ]}
              components={mermaidComponents} >
            {markdownContent}</ReactMarkdown>
        </div>
      ) : (
        <span className="text-slate-400">{isStreaming ? "Preparing response..." : "No response yet."}</span>
      )}

      {isStreaming && (
        <LoadingIndicator sid={sid} page="chat" placeholderText={progressPlaceholder} />
      )}
      {!isStreaming && tokensUsed !== null && (
        <p className={uiClasses.loading.usage}>
          {model ? `Model: ${model}` : ""}
          {tokensUsed !== null ? ` | Tokens used: ${tokensUsed}` : ""}
        </p>
      )}
    </div>
  );
}