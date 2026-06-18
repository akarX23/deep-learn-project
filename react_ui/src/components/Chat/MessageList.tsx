import type { ChatMessage } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";
import { StreamResponseBox } from "./StreamResponseBox";
import { UserMessage } from "./UserMessage";

interface MessageListProps {
  messages: ChatMessage[];
  sid: string | null;
  activeStreamMessageId: string | null;
  progressPlaceholder: string;
  onAssistantStreamDone: (messageId: string) => void;
}

export function MessageList({
  messages,
  sid,
  activeStreamMessageId,
  progressPlaceholder,
  onAssistantStreamDone
}: MessageListProps): JSX.Element {
  return (
    <div className={uiClasses.chat.messages}>
      {messages.map((message) => (
        <div
          key={message.id}
          className={[
            uiClasses.chat.bubble,
            message.role === "user"
              ? uiClasses.chat.userBubble
              : message.info
                ? uiClasses.chat.infoBubble
                : uiClasses.chat.assistantBubble
          ].join(" ")}
        >
          {message.role === "user" ? (
            <UserMessage content={message.content} attachments={message.attachments} />
          ) : message.info ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <StreamResponseBox
              sid={sid}
              messageId={message.id}
              isActive={activeStreamMessageId === message.id}
              initialContent={message.content}
              progressPlaceholder={progressPlaceholder}
              onDone={() => onAssistantStreamDone(message.id)}
            />
          )}
        </div>
      ))}
    </div>
  );
}
