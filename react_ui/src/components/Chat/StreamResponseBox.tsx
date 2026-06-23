import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { rehypeMermaid, MermaidBlock } from 'react-markdown-mermaid';
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type { ClarifyUserLevelEventBody, StreamCompletionPayload, StreamTokensEventBody } from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";
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
  const [chartCode, setChartCode] = useState<string>("");

  const previousFieldRef = useRef<string | null>(null);
  const revealTimerRef = useRef<number | null>(null);
  
  // Streaming State Tracking
  const incomingBufferRef = useRef<string>(initialContent);
  const displayedLengthRef = useRef<number>(initialContent.length);
  const isDoneRef = useRef<boolean>(false);
  const onDoneFiredRef = useRef<boolean>(false);
  const completionDataRef = useRef<{ tokens_used?: number; model?: string }>({});

  const _STREAM_FLUSH_INTERVAL_MS = 20;
  const _STREAM_FLUSH_CHARS_PER_TICK = 5;

  const isDiagramField = (value: string): boolean => value.toLowerCase() === "diagram";

  // 1. Reset state whenever the message context changes
  useEffect(() => {
    setMarkdownContent(initialContent);
    setIsStreaming(isActive);
    setTokensUsed(initialTokensUsed ?? null);
    setModel(initialModel ?? null);
    setRevealPulse(false);
    
    incomingBufferRef.current = initialContent;
    displayedLengthRef.current = initialContent.length;
    isDoneRef.current = false;
    onDoneFiredRef.current = false;
    previousFieldRef.current = null;
    completionDataRef.current = {};
  }, [initialContent, initialTokensUsed, initialModel, isActive, messageId]);

  // 2. The Typewriter "Catch-up" Loop
  useEffect(() => {
    if (!isActive) return;

    const ticker = window.setInterval(() => {
      const currentLen = displayedLengthRef.current;
      const targetLen = incomingBufferRef.current.length;

      if (currentLen < targetLen) {
        // We have characters to reveal
        const nextLen = Math.min(currentLen + _STREAM_FLUSH_CHARS_PER_TICK, targetLen);
        const nextContent = incomingBufferRef.current.slice(0, nextLen);
        
        displayedLengthRef.current = nextLen;
        setMarkdownContent(nextContent);
      } else if (isDoneRef.current && !onDoneFiredRef.current) {
        // Buffer is fully drained AND stream is marked as done
        onDoneFiredRef.current = true;
        setIsStreaming(false);
        setTokensUsed(completionDataRef.current.tokens_used ?? null);
        setModel(completionDataRef.current.model ?? null);
        
        onDone({
          messageId,
          fullContent: incomingBufferRef.current,
          tokens_used: completionDataRef.current.tokens_used,
          model: completionDataRef.current.model
        });
      }
    }, _STREAM_FLUSH_INTERVAL_MS);

    return () => window.clearInterval(ticker);
  }, [isActive, messageId, onDone]);

  // 3. Cleanup pulse timer on unmount
  useEffect(() => {
    return () => {
      if (revealTimerRef.current !== null) {
        window.clearTimeout(revealTimerRef.current);
      }
    };
  }, []);

  // 4. Helper function to cleanly append text and handle animations
  const handleAppendToBuffer = useCallback((text: string, markDone: boolean = false) => {
    if (text) {
      setRevealPulse(true);
      if (revealTimerRef.current !== null) {
        window.clearTimeout(revealTimerRef.current);
      }
      revealTimerRef.current = window.setTimeout(() => {
        setRevealPulse(false);
      }, 170);
      
      incomingBufferRef.current += text;
    }
    
    if (markDone) {
      isDoneRef.current = true;
    }
  }, []);

  // 5. WebSocket Event Handlers
  useSocketEvent<StreamTokensEventBody>(
    WebSocketEvents.STREAM_TOKENS_SKT,
    useCallback(
      (payload) => {
        if (!isActive || !sid || payload.sid !== sid || payload.from_service !== "teaching-agent") {
          return;
        }

        const field = typeof payload.data.field === "string" ? payload.data.field.trim() : "";
        let sectionHeading = "";
        let token = typeof payload.data.token === "string" ? payload.data.token : "";

        if (field && field !== previousFieldRef.current) {
          sectionHeading = `\n\n## ${field.charAt(0).toUpperCase() + field.slice(1)}\n\n`;
          previousFieldRef.current = field;
        }

        if (isDiagramField(field)) {
          token = `${sectionHeading}\`\`\`mermaid\n${token}\n\`\`\``;
          console.log("Diagram: ", token)
          setChartCode(token);
          return;
        }

        // Flag as done, and let the interval hook catch up naturally
        if (payload.data.done === true) {
          completionDataRef.current = {
            tokens_used: typeof payload.data.tokens_used === "number" ? payload.data.tokens_used : undefined,
            model: typeof payload.data.model === "string" && payload.data.model.trim().length > 0 ? payload.data.model.trim() : undefined
          };
          handleAppendToBuffer("", true);
          return;
        }

        const tokenAppend = `${sectionHeading}${token}`;
        handleAppendToBuffer(tokenAppend, false);
      },
      [isActive, sid, handleAppendToBuffer]
    )
  );

  useSocketEvent<ClarifyUserLevelEventBody>(
    WebSocketEvents.CLARIFY_USER_LEVEL_SKT, 
    useCallback(
      (payload) => {
        if (!isActive || !sid || payload.sid !== sid) return;
        
        // Append cleanly to the buffer instead of overwriting the state
        const message = "\n\n**Notice:** As an AI Tutor, I need more information to provide a detailed response. Please clarify what you would like to learn.";
        handleAppendToBuffer(message, true);
      },
      [isActive, sid, handleAppendToBuffer]
    )
  );
  
  useSocketEvent(
    WebSocketEvents.WORKFLOW_COMPLETE_SKT, 
    useCallback(
      (payload) => {
        if (!isActive || !sid || payload.sid !== sid) return;
        
        if (payload.status === "blocked") {
          // Append cleanly to the buffer instead of overwriting the state
          const message = "\n\n**Notice:** As an AI Tutor, I have detected a potentially malicious query and have blocked the workflow. Please modify your query and try again.";
          handleAppendToBuffer(message, true);
        }
      },
      [isActive, sid, handleAppendToBuffer]
    )
  );

  return (
    <div className={uiClasses.chat.markdownBox}>
      {markdownContent || incomingBufferRef.current ? (
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
      {chartCode && (
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
            {chartCode}
          </ReactMarkdown>
        </div>
        )
      }
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