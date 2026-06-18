import ReactMarkdown from "react-markdown";
import { uiClasses } from "../../styles/uiClasses";
import { LoadingIndicator } from "./LoadingIndicator";

interface StreamResponseBoxProps {
  markdownContent: string;
  isStreaming: boolean;
  progressPlaceholder: string;
}

export function StreamResponseBox({
  markdownContent,
  isStreaming,
  progressPlaceholder
}: StreamResponseBoxProps): JSX.Element {
  return (
    <div className={uiClasses.chat.markdownBox}>
      {markdownContent ? (
        <ReactMarkdown>{markdownContent}</ReactMarkdown>
      ) : (
        <span className="text-slate-400">{isStreaming ? "Preparing response..." : "No response yet."}</span>
      )}

      {isStreaming && <LoadingIndicator placeholderText={progressPlaceholder} />}
    </div>
  );
}