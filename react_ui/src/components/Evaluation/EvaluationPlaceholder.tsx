import { useCallback } from "react";
import { LoadingIndicator } from "../Chat/LoadingIndicator";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type {
  MCQOption,
  QuestionResult,
  Quiz,
  QuizEvaluationStreamPayload,
  SubmittedAnswer,
  StreamTokensEventBody,
  SWOTAnalysis
} from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";
import type { QuizSectionContext } from "../Quiz/QuizPlaceholder";

export interface EvaluationSectionContext {
  status: "idle" | "loading" | "ready" | "error";
  payload: QuizEvaluationStreamPayload | null;
  error: string | null;
}

interface EvaluationPlaceholderProps {
  sid: string | null;
  context: EvaluationSectionContext;
  quizContext: QuizSectionContext | null;
  onContextChange: (context: EvaluationSectionContext) => void;
}

function getScoreTone(percentage: number): { bar: string; text: string; chip: string } {
  if (percentage >= 85) {
    return {
      bar: "bg-emerald-400",
      text: "text-emerald-200",
      chip: "border-emerald-300/40 bg-emerald-300/15 text-emerald-100"
    };
  }

  if (percentage >= 60) {
    return {
      bar: "bg-amber-300",
      text: "text-amber-200",
      chip: "border-amber-300/40 bg-amber-300/15 text-amber-100"
    };
  }

  return {
    bar: "bg-rose-400",
    text: "text-rose-200",
    chip: "border-rose-300/40 bg-rose-300/15 text-rose-100"
  };
}

function formatActionLabel(action: string | undefined): string {
  if (!action) {
    return "n/a";
  }
  return action.replace("-", " ");
}

function getOptionTone(
  optionId: string,
  selectedOptionIds: string[],
  option: MCQOption
): { classes: string } {
  const wasSelected = selectedOptionIds.includes(optionId);
  const isCorrect = option.is_correct;

  if (wasSelected && isCorrect) {
    return {
      classes: "border-emerald-300/30 bg-emerald-400/10 text-emerald-100"
    };
  }

  if (wasSelected && !isCorrect) {
    return {
      classes: "border-rose-300/30 bg-rose-400/10 text-rose-100"
    };
  }

  if (!wasSelected && isCorrect) {
    return {
      classes: "border-amber-300/30 bg-amber-400/10 text-amber-100"
    };
  }

  return {
    classes: "border-slate-700 bg-slate-900/70 text-slate-300"
  };
}

function renderSwotCard(title: string, values: string[], classes: string): JSX.Element {
  return (
    <article className={`rounded-xl border p-4 ${classes}`}>
      <h4 className="text-sm font-semibold uppercase tracking-wide">{title}</h4>
      {values.length === 0 ? (
        <p className="mt-2 text-sm opacity-80">No items available.</p>
      ) : (
        <ul className="mt-2 space-y-1 text-sm">
          {values.map((item, index) => (
            <li key={`${title}-${index}`}>- {item}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

function getQuestionTitle(quiz: Quiz | undefined, questionId: string, index: number): string {
  const question = quiz?.questions.find((entry) => entry.id === questionId);
  if (!question) {
    return `Q${index + 1}`;
  }
  return `Q${index + 1}: ${question.prompt}`;
}

function renderQuestionResult(
  quiz: Quiz | undefined,
  submittedAnswer: SubmittedAnswer | undefined,
  questionResult: QuestionResult,
  index: number
): JSX.Element {
  const scorePercent =
    questionResult.max_score > 0 ? (questionResult.score / questionResult.max_score) * 100 : 0;
  const tone = getScoreTone(scorePercent);
  const question = quiz?.questions.find((entry) => entry.id === questionResult.question_id);
  const selectedOptionIds = submittedAnswer?.selected_option_ids ?? [];

  return (
    <article
      key={`${questionResult.question_id}-${index}`}
      className="rounded-xl border border-slate-700 bg-slate-950/60 p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-100">
          {getQuestionTitle(quiz, questionResult.question_id, index)}
        </h4>
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${tone.chip}`}>
          {questionResult.score}/{questionResult.max_score}
        </span>
      </div>

      {typeof questionResult.is_correct === "boolean" && (
        <p className="mt-2 text-sm text-slate-300">
          Result: {questionResult.is_correct ? "Correct" : "Incorrect"}
        </p>
      )}

      {!!questionResult.wrong_answer_explanation && (
        <p className="mt-2 rounded-md border border-rose-300/30 bg-rose-400/10 p-2 text-sm text-rose-100">
          Why this was incorrect: {questionResult.wrong_answer_explanation}
        </p>
      )}

      {!!questionResult.topic_deep_dive && (
        <p className="mt-2 rounded-md border border-blue-300/30 bg-blue-400/10 p-2 text-sm text-blue-100">
          Topic deep dive: {questionResult.topic_deep_dive}
        </p>
      )}

      {(questionResult.per_option_explanations ?? []).length > 0 && (
        <div className="mt-3 space-y-2">
          <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
            Option Explanations
          </h5>
          {(questionResult.per_option_explanations ?? []).map((entry) => (
            <p
              key={`${questionResult.question_id}-${entry.option_id}-${entry.explanation_type}`}
              className="rounded-md border border-slate-700 bg-slate-900/80 p-2 text-sm text-slate-200"
            >
              Option {entry.option_id}: {entry.explanation}
            </p>
          ))}
        </div>
      )}

      {(question?.options ?? []).length > 0 && (
        <div className="mt-3 space-y-2">
          <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
            Marked Options
          </h5>
          {(question?.options ?? []).map((option) => {
            const toneInfo = getOptionTone(option.id, selectedOptionIds, option);
            return (
              <p
                key={`${questionResult.question_id}-${option.id}`}
                className={`rounded-md border p-2 text-sm ${toneInfo.classes}`}
              >
                {option.text}
              </p>
            );
          })}
        </div>
      )}

      {!!questionResult.model_answer && (
        <p className="mt-3 rounded-md border border-emerald-300/30 bg-emerald-400/10 p-2 text-sm text-emerald-100">
          Model answer: {questionResult.model_answer}
        </p>
      )}

      {!!questionResult.feedback && (
        <p className="mt-2 rounded-md border border-amber-300/30 bg-amber-400/10 p-2 text-sm text-amber-100">
          Feedback: {questionResult.feedback}
        </p>
      )}
    </article>
  );
}

export function EvaluationPlaceholder({
  sid,
  context,
  quizContext,
  onContextChange
}: EvaluationPlaceholderProps): JSX.Element {
  useSocketEvent<StreamTokensEventBody>(
    WebSocketEvents.STREAM_TOKENS_SKT,
    useCallback(
      (payload) => {
        if (!sid || payload.sid !== sid) {
          return;
        }
        if (payload.from_service !== "eval-agent") {
          return;
        }

        const eventPayload = payload.data as unknown as QuizEvaluationStreamPayload;
        if (!eventPayload?.result) {
          return;
        }

        onContextChange({
          status: "ready",
          payload: eventPayload,
          error: null
        });
      },
      [onContextChange, sid]
    )
  );

  const evalResult = context.payload?.result;
  const quiz = quizContext?.quiz ?? undefined;
  const answerByQuestionId = Object.fromEntries(
    (quizContext?.answers ?? []).map((answer) => [answer.question_id, answer] as const)
  );
  const swot: SWOTAnalysis | undefined = context.payload?.swot;

  const score = evalResult?.overall_score ?? 0;
  const maxScore = evalResult?.max_score ?? 1;
  const scorePercent = evalResult?.overall_percentage ?? (score / maxScore) * 100;
  const safePercent = Math.max(0, Math.min(100, scorePercent));
  const scoreTone = getScoreTone(safePercent);
  const mcqSubtotal = evalResult?.mcq_subtotal ?? 0;
  const descriptiveSubtotal = evalResult?.descriptive_subtotal ?? 0;

  return (
    <section className={uiClasses.placeholder.panel}>
      <h2 className={uiClasses.placeholder.title}>Evaluation</h2>

      {context.status === "idle" && (
        <p className="mt-2 text-slate-300">Submit a quiz to see evaluation.</p>
      )}

      {context.status === "loading" && (
        <div className="mt-3">
          <LoadingIndicator placeholderText="Evaluating Quiz" />
        </div>
      )}

      {context.status === "error" && <p className="mt-2 text-sm text-rose-300">{context.error}</p>}

      {context.status === "ready" && evalResult && (
        <div className="mt-4 space-y-5">
          <section className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-base font-semibold text-slate-100">Summary</h3>
              <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${scoreTone.chip}`}>
                {score}/{maxScore}
              </span>
            </div>

            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div className={`h-2 rounded-full transition-all ${scoreTone.bar}`} style={{ width: `${safePercent}%` }} />
            </div>

            <p className={`mt-2 text-sm font-medium ${scoreTone.text}`}>{safePercent.toFixed(1)}% overall</p>

            <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-300 md:grid-cols-2">
              <p>MCQ subtotal: {mcqSubtotal.toFixed(2)}</p>
              <p>Descriptive subtotal: {descriptiveSubtotal.toFixed(2)}</p>
              <p>
                Recommended action: <span className="font-medium text-slate-100">{formatActionLabel(evalResult.recommended_action)}</span>
              </p>
              <p>
                Weak sub-concepts: <span className="font-medium text-slate-100">{evalResult.weak_sub_concepts.length}</span>
              </p>
            </div>

            {evalResult.weak_sub_concepts.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {evalResult.weak_sub_concepts.map((item, index) => (
                  <span
                    key={`${item}-${index}`}
                    className="rounded-md border border-rose-300/30 bg-rose-400/10 px-2 py-1 text-xs text-rose-100"
                  >
                    {item}
                  </span>
                ))}
              </div>
            )}
          </section>

          <section className="space-y-3">
            <h3 className="text-base font-semibold text-slate-100">Question Review</h3>
            {evalResult.question_results.map((questionResult, index) =>
              renderQuestionResult(
                quiz,
                answerByQuestionId[questionResult.question_id] as SubmittedAnswer | undefined,
                questionResult,
                index
              )
            )}
          </section>

          {swot && (
            <section className="space-y-3">
              <h3 className="text-base font-semibold text-slate-100">SWOT Analysis</h3>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {renderSwotCard(
                  "Strengths",
                  swot.strengths,
                  "border-emerald-300/30 bg-emerald-400/10 text-emerald-100"
                )}
                {renderSwotCard(
                  "Weaknesses",
                  swot.weaknesses,
                  "border-rose-300/30 bg-rose-400/10 text-rose-100"
                )}
                {renderSwotCard(
                  "Opportunities",
                  swot.opportunities,
                  "border-blue-300/30 bg-blue-400/10 text-blue-100"
                )}
                {renderSwotCard(
                  "Threats",
                  swot.threats,
                  "border-amber-300/30 bg-amber-400/10 text-amber-100"
                )}
              </div>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
