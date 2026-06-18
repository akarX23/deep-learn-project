export interface StreamTokensEventBody {
  from_service: string;
  sid: string;
  data: {
    field?: string;
    token?: string;
    done?: boolean;
    tokens_used?: number;
    [key: string]: unknown;
  };
}

export interface ClarifyUserLevelEvent {
  request_id: string;
  user_prompt: string;
  sid: string;
  reason?: string;
}

export interface UserRequest {
  user_prompt: string;
  user_level: string[];
  sid: string;
}

export interface ChatAttachment {
  name: string;
  sizeBytes: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming: boolean;
  tokens_used?: number;
  info?: boolean;
  attachments?: ChatAttachment[];
}

export interface StreamCompletionPayload {
  messageId: string;
  fullContent: string;
  tokens_used?: number;
}

export const WebSocketEvents = {
  STREAM_TOKENS_SKT: "stream-tokens-skt",
  CLARIFY_USER_LEVEL_SKT: "clarify-user-level-skt"
} as const;
