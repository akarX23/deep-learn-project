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

export type QuestionType = "mcq-single" | "mcq-multi" | "descriptive";

export interface MCQOption {
  id: string;
  text: string;
  is_correct: boolean;
  explanation: string;
}

export interface QuizQuestion {
  id: string;
  type?: QuestionType;
  prompt: string;
  sub_concept: string;
  max_points?: number;
  options?: MCQOption[];
  topic_deep_dive?: string;
  rubric?: string[];
}

export interface QuizMetadata {
  question_type_counts?: Record<string, number>;
  total_questions?: number;
  max_score?: number;
  mcq_max_score?: number;
  descriptive_max_score?: number;
  ui_hints?: Record<string, unknown>;
}

export interface Quiz {
  quiz_id: string;
  topic: string;
  questions: QuizQuestion[];
  metadata?: QuizMetadata;
}

export interface QuizAgentMetadata {
  topic: string;
  tokens_used: number;
  model: string;
}

export interface QuizAgentOutput {
  status: "generated" | "evaluated" | "error";
  quiz?: Quiz;
  result?: Record<string, unknown>;
  metadata?: QuizAgentMetadata;
  errors?: string[];
}

export interface SubmittedAnswer {
  question_id: string;
  selected_option_ids: string[];
  free_text: string;
}

export const WebSocketEvents = {
  STREAM_TOKENS_SKT: "stream-tokens-skt",
  CLARIFY_USER_LEVEL_SKT: "clarify-user-level-skt"
} as const;
