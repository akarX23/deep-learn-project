import { useCallback, useEffect, useMemo, useState } from "react";
import { LoadingIndicator } from "../Chat/LoadingIndicator";
import { useSocketEvent } from "../../hooks/useSocketEvent";
import type {
  Quiz,
  QuizAgentOutput,
  QuizQuestion,
  StreamTokensEventBody,
  SubmittedAnswer
} from "../../schemas";
import { WebSocketEvents } from "../../schemas";
import { uiClasses } from "../../styles/uiClasses";

interface QuizPlaceholderProps {
  sid: string | null;
  hasInitiatedChat: boolean;
  isRequestingQuiz: boolean;
  isSubmittingEvaluation?: boolean;
  onRequestQuiz: () => Promise<void>;
  onSubmitEvaluation?: (payload: { quiz: Quiz; answers: SubmittedAnswer[] }) => Promise<void>;
  onContextChange?: (context: QuizSectionContext) => void;
}

export interface QuizSectionContext {
  quiz: Quiz | null;
  answers: SubmittedAnswer[];
  isLoading: boolean;
  isSubmittingEvaluation: boolean;
  error: string | null;
}

function getQuestionMode(question: QuizQuestion): "single" | "multi" | "descriptive" {
  if (question.rubric && question.rubric.length > 0) {
    return "descriptive";
  }

  if (!question.options || question.options.length === 0) {
    return "descriptive";
  }

  if (question.type === "mcq-multi") {
    return "multi";
  }

  if (question.type === "mcq-single") {
    return "single";
  }

  const correctCount = question.options.filter((option) => option.is_correct).length;
  return correctCount > 1 ? "multi" : "single";
}

export function QuizPlaceholder({
  sid,
  hasInitiatedChat,
  isRequestingQuiz,
  isSubmittingEvaluation = false,
  onRequestQuiz,
  onSubmitEvaluation,
  onContextChange
}: QuizPlaceholderProps): JSX.Element {
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<SubmittedAnswer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasReceivedQuizEvent, setHasReceivedQuizEvent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!onContextChange) {
      return;
    }

    onContextChange({
      quiz,
      answers,
      isLoading,
      isSubmittingEvaluation,
      error
    });
  }, [answers, error, isLoading, isSubmittingEvaluation, onContextChange, quiz]);

  useSocketEvent<StreamTokensEventBody>(
    WebSocketEvents.STREAM_TOKENS_SKT,
    useCallback(
      (payload) => {
        if (!sid || payload.sid !== sid) {
          return;
        }
        if (payload.from_service !== "quiz-agent") {
          return;
        }

        setHasReceivedQuizEvent(true);
        setIsLoading(true);

        const data = payload.data as unknown as QuizAgentOutput;
        if (typeof data.status !== "string") {
          return;
        }

        if (data.status === "error") {
          setError((data.errors && data.errors[0]) || "Failed to generate quiz.");
          setIsLoading(false);
          return;
        }

        if (data.status === "generated" && data.quiz) {
          setQuiz(data.quiz);
          setAnswers(
            data.quiz.questions.map((question) => ({
              question_id: question.id,
              selected_option_ids: [],
              free_text: ""
            }))
          );
          setError(null);
          setIsLoading(false);
        }
      },
      [sid]
    )
  );

  const handleGenerateQuiz = useCallback(async (): Promise<void> => {
    setError(null);
    setIsLoading(true);

    try {
      await onRequestQuiz();
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Failed to submit quiz request.";
      setError(message);
      setIsLoading(false);
    }
  }, [onRequestQuiz]);

  const handleSubmitAnswers = useCallback(async (): Promise<void> => {
    if (!quiz || !onSubmitEvaluation) {
      return;
    }

    setError(null);
    try {
      await onSubmitEvaluation({ quiz, answers });
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "Failed to submit quiz answers.";
      setError(message);
    }
  }, [answers, onSubmitEvaluation, quiz]);

  const answerByQuestionId = useMemo(() => {
    const entries = answers.map((answer) => [answer.question_id, answer] as const);
    return Object.fromEntries(entries);
  }, [answers]);

  const updateSingleChoice = (questionId: string, optionId: string): void => {
    setAnswers((prev) =>
      prev.map((answer) =>
        answer.question_id === questionId
          ? { ...answer, selected_option_ids: [optionId], free_text: "" }
          : answer
      )
    );
  };

  const updateMultiChoice = (questionId: string, optionId: string, checked: boolean): void => {
    setAnswers((prev) =>
      prev.map((answer) => {
        if (answer.question_id !== questionId) {
          return answer;
        }

        const nextIds = checked
          ? [...answer.selected_option_ids, optionId]
          : answer.selected_option_ids.filter((id) => id !== optionId);

        return {
          ...answer,
          selected_option_ids: Array.from(new Set(nextIds)),
          free_text: ""
        };
      })
    );
  };

  const updateSubjective = (questionId: string, value: string): void => {
    setAnswers((prev) =>
      prev.map((answer) =>
        answer.question_id === questionId
          ? { ...answer, free_text: value, selected_option_ids: [] }
          : answer
      )
    );
  };

  return (
    <section className={uiClasses.placeholder.panel}>
      <h2 className={uiClasses.placeholder.title}>Quiz</h2>

      <div className="mt-3">
        <button
          type="button"
          className={uiClasses.input.submit}
          disabled={!hasInitiatedChat || isRequestingQuiz || isLoading}
          onClick={handleGenerateQuiz}
        >
          {hasReceivedQuizEvent ? "Refresh Questions" : "Generate Quiz from Chat"}
        </button>
      </div>

      {isLoading && <LoadingIndicator placeholderText="Waiting for quiz generation..." />}
      {error && <p className={uiClasses.chat.errorText}>{error}</p>}

      {!isLoading && !error && !quiz && (
        <p className={uiClasses.placeholder.text}>Quiz has not been generated yet.</p>
      )}

      {!isLoading && !error && quiz && (
        <div className="mt-4 space-y-4">
          {quiz.questions.map((question, index) => {
            const mode = getQuestionMode(question);
            const answer = answerByQuestionId[question.id];

            return (
              <div key={question.id} className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                <p className="mb-2 text-sm text-slate-300">Q{index + 1}</p>
                <p className="mb-3 text-slate-100">{question.prompt}</p>

                {mode === "single" && (
                  <div className="space-y-2">
                    {question.options?.map((option) => (
                      <label key={option.id} className="flex cursor-pointer items-start gap-2 text-sm text-slate-200">
                        <input
                          type="radio"
                          name={`q-${question.id}`}
                          checked={answer?.selected_option_ids.includes(option.id) ?? false}
                          onChange={() => updateSingleChoice(question.id, option.id)}
                        />
                        <span>{option.text}</span>
                      </label>
                    ))}
                  </div>
                )}

                {mode === "multi" && (
                  <div className="space-y-2">
                    {question.options?.map((option) => (
                      <label key={option.id} className="flex cursor-pointer items-start gap-2 text-sm text-slate-200">
                        <input
                          type="checkbox"
                          checked={answer?.selected_option_ids.includes(option.id) ?? false}
                          onChange={(event) =>
                            updateMultiChoice(question.id, option.id, event.target.checked)
                          }
                        />
                        <span>{option.text}</span>
                      </label>
                    ))}
                  </div>
                )}

                {mode === "descriptive" && (
                  <textarea
                    value={answer?.free_text ?? ""}
                    onChange={(event) => updateSubjective(question.id, event.target.value)}
                    rows={4}
                    placeholder="Write your answer here..."
                    className={uiClasses.input.textarea}
                  />
                )}
              </div>
            );
          })}

          <div className="pt-2">
            <button
              type="button"
              onClick={() => {
                void handleSubmitAnswers();
              }}
              disabled={isSubmittingEvaluation || !onSubmitEvaluation}
              className={uiClasses.input.submit}
            >
              Submit Answers
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
