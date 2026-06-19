export interface StreamTokensEventBody {
  from_service: string;
  sid: string;
  data: Record<string, unknown>;
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
  result?: QuizResult;
  metadata?: QuizAgentMetadata;
  errors?: string[];
}

export interface SubmittedAnswer {
  question_id: string;
  selected_option_ids: string[];
  free_text: string;
}

export interface PerOptionExplanation {
  option_id: string;
  explanation_type: "wrong-selected" | "missed-correct" | string;
  explanation: string;
}

export interface QuestionResult {
  question_id: string;
  score: number;
  max_score: number;
  is_correct?: boolean;
  wrong_answer_explanation?: string;
  topic_deep_dive?: string;
  per_option_explanations?: PerOptionExplanation[];
  model_answer?: string;
  feedback?: string;
  confidence_score?: number;
}

export interface QuizResult {
  overall_score: number;
  max_score: number;
  overall_percentage: number;
  mcq_subtotal: number;
  descriptive_subtotal: number;
  question_results: QuestionResult[];
  weak_sub_concepts: string[];
  recommended_action: "re-teach" | "practice-more" | "advance";
}

export interface SWOTAnalysis {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

export interface QuizEvaluationStreamPayload {
  result: QuizResult;
  swot: SWOTAnalysis;
}

export const WebSocketEvents = {
  STREAM_TOKENS_SKT: "stream-tokens-skt",
  CLARIFY_USER_LEVEL_SKT: "clarify-user-level-skt"
} as const;
