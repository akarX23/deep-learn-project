import type { ChatAttachment } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";

interface UserMessageProps {
  content: string;
  attachments?: ChatAttachment[];
}

export function UserMessage({ content, attachments = [] }: UserMessageProps): JSX.Element {
  return (
    <div className="space-y-2">
      <div className="whitespace-pre-wrap">{content}</div>
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {attachments.map((attachment) => (
            <span key={`${attachment.name}-${attachment.sizeBytes}`} className={uiClasses.chat.attachmentChip}>
              {attachment.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}