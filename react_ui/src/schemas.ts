export interface StreamTokensEventBody {
  from_service: string;
  sid: string;
  data: Record<string, any>;
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

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming: boolean;
  info?: boolean;
}

export const WebSocketEvents = {
  STREAM_TOKENS_SKT: "stream-tokens-skt",
  CLARIFY_USER_LEVEL_SKT: "clarify-user-level-skt"
} as const;
