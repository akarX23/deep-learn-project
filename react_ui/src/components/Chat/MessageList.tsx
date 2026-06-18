import type { ChatMessage } from "../../schemas";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps): JSX.Element {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: 180, marginBottom: 16 }}>
      {messages.map((message) => (
        <div
          key={message.id}
          style={{
            alignSelf: message.role === "user" ? "flex-end" : "flex-start",
            background: message.role === "user" ? "#dbeafe" : "#f3f4f6",
            border: "1px solid #e5e7eb",
            borderRadius: 10,
            padding: 10,
            maxWidth: "80%",
            whiteSpace: "pre-wrap"
          }}
        >
          {message.content || (message.isStreaming ? "..." : "")}
        </div>
      ))}
    </div>
  );
}
