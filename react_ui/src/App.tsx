import { useCallback, useEffect, useState } from "react";
import { ChatWindow } from "./components/Chat/ChatWindow";
import {
  EvaluationPlaceholder,
  type EvaluationSectionContext
} from "./components/Evaluation/EvaluationPlaceholder";
import { Navbar } from "./components/Navbar";
import { Navigation } from "./components/Navigation";
import { QuizPlaceholder } from "./components/Quiz/QuizPlaceholder";
import type { ChatWindowContext } from "./components/Chat/ChatWindow";
import type { QuizSectionContext } from "./components/Quiz/QuizPlaceholder";
import { submitChatRequest, submitQuizEvaluateRequest, submitQuizRequest } from "./services/api";
import { getSocket } from "./services/socket";
import { uiClasses } from "./styles/uiClasses";

type Section = "chat" | "quiz" | "evaluation";

interface SectionContexts {
  chat: ChatWindowContext | null;
  quiz: QuizSectionContext | null;
  evaluation: EvaluationSectionContext;
}

export default function App(): JSX.Element {
  const [currentSection, setCurrentSection] = useState<Section>("chat");
  const [socketId, setSocketId] = useState<string | null>(null);
  const [isRequestingQuiz, setIsRequestingQuiz] = useState(false);
  const [sectionContexts, setSectionContexts] = useState<SectionContexts>({
    chat: null,
    quiz: null,
    evaluation: {
      status: "idle",
      payload: null,
      error: null
    }
  });

  const hasInitiatedChat =
    sectionContexts.chat?.messages.some((message) => message.role === "user") ?? false;

  useEffect(() => {
    const socket = getSocket();

    const handleConnect = (): void => {
      setSocketId(socket.id ?? null);
    };

    const handleDisconnect = (): void => {
      setSocketId(null);
    };

    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);

    if (socket.connected) {
      handleConnect();
    }

    return () => {
      socket.off("connect", handleConnect);
      socket.off("disconnect", handleDisconnect);
    };
  }, []);

  const handleChatContextChange = useCallback((context: ChatWindowContext): void => {
    setSectionContexts((prev) => ({
      ...prev,
      chat: context
    }));
  }, []);

  const handleQuizContextChange = useCallback((context: QuizSectionContext): void => {
    setSectionContexts((prev) => ({
      ...prev,
      quiz: context
    }));
  }, []);

  const handleEvaluationContextChange = useCallback((context: EvaluationSectionContext): void => {
    setSectionContexts((prev) => ({
      ...prev,
      evaluation: context
    }));
  }, []);

  const handleQuizRequest = useCallback(async (): Promise<void> => {
    if (!socketId) {
      throw new Error("Socket is not connected yet.");
    }

    const messages = sectionContexts.chat?.messages ?? [];
    const firstUserMessage = messages.find(
      (message) => message.role === "user" && message.content.trim().length > 0
    );

    if (!firstUserMessage) {
      throw new Error("No user prompt found to generate quiz.");
    }

    const teachingMaterial = messages
      .filter(
        (message) =>
          message.role === "assistant" &&
          !message.info &&
          message.content.trim().length > 0
      )
      .map((message) => message.content.trim())
      .join("\n\n");

    if (teachingMaterial.length === 0) {
      throw new Error("No teaching material found in chat yet.");
    }

    setIsRequestingQuiz(true);
    try {
      await submitQuizRequest({
        sid: socketId,
        userPrompt: firstUserMessage.content.trim(),
        teachingMaterial
      });
    } finally {
      setIsRequestingQuiz(false);
    }
  }, [sectionContexts.chat?.messages, socketId]);

  const handleSubmitQuizEvaluation = useCallback(
    async ({
      quiz,
      answers
    }: {
      quiz: NonNullable<QuizSectionContext["quiz"]>;
      answers: QuizSectionContext["answers"];
    }): Promise<void> => {
      if (!socketId) {
        throw new Error("Socket is not connected yet.");
      }

      setSectionContexts((prev) => ({
        ...prev,
        evaluation: {
          status: "loading",
          payload: null,
          error: null
        }
      }));
      setCurrentSection("evaluation");

      try {
        await submitQuizEvaluateRequest({
          sid: socketId,
          quiz,
          answers
        });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Failed to submit quiz evaluation request.";
        setSectionContexts((prev) => ({
          ...prev,
          evaluation: {
            status: "error",
            payload: null,
            error: message
          }
        }));
        throw error;
      }
    },
    [socketId]
  );

  return (
    <main className={uiClasses.layout.page}>
      <div className={uiClasses.layout.container}>
        <Navbar title="A_Z Tutor" />
        <Navigation current={currentSection} onSelect={setCurrentSection} />
        <div className={uiClasses.layout.card}>
          <div className={currentSection === "chat" ? "block" : "hidden"}>
            <ChatWindow
              sid={socketId}
              onContextChange={handleChatContextChange}
              onSubmitRequest={(prompt, files) =>
                submitChatRequest({
                  userPrompt: prompt,
                  sid: socketId ?? "",
                  userLevel: [],
                  files
                })
              }
            />
          </div>

          <div className={currentSection === "quiz" ? "block" : "hidden"}>
            <QuizPlaceholder
              sid={socketId}
              hasInitiatedChat={hasInitiatedChat}
              isRequestingQuiz={isRequestingQuiz}
              isSubmittingEvaluation={sectionContexts.evaluation.status === "loading"}
              onRequestQuiz={handleQuizRequest}
              onSubmitEvaluation={handleSubmitQuizEvaluation}
              onContextChange={handleQuizContextChange}
            />
          </div>

          <div className={currentSection === "evaluation" ? "block" : "hidden"}>
            <EvaluationPlaceholder
              sid={socketId}
              context={sectionContexts.evaluation}
              quizContext={sectionContexts.quiz}
              onContextChange={handleEvaluationContextChange}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
