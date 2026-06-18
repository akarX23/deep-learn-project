import { useCallback, useEffect, useState } from "react";
import { ChatWindow } from "./components/Chat/ChatWindow";
import { EvaluationPlaceholder } from "./components/Evaluation/EvaluationPlaceholder";
import { Navbar } from "./components/Navbar";
import { Navigation } from "./components/Navigation";
import { QuizPlaceholder } from "./components/Quiz/QuizPlaceholder";
import type { ChatWindowContext } from "./components/Chat/ChatWindow";
import type { QuizSectionContext } from "./components/Quiz/QuizPlaceholder";
import { submitChatRequest } from "./services/api";
import { getSocket } from "./services/socket";
import { uiClasses } from "./styles/uiClasses";

type Section = "chat" | "quiz" | "evaluation";

interface SectionContexts {
  chat: ChatWindowContext | null;
  quiz: QuizSectionContext | null;
  evaluation: Record<string, never>;
}

export default function App(): JSX.Element {
  const [currentSection, setCurrentSection] = useState<Section>("chat");
  const [socketId, setSocketId] = useState<string | null>(null);
  const [sectionContexts, setSectionContexts] = useState<SectionContexts>({
    chat: null,
    quiz: null,
    evaluation: {}
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

  return (
    <main className={uiClasses.layout.page}>
      <div className={uiClasses.layout.container}>
        <Navbar title="AI Tutor" />
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
              onContextChange={handleQuizContextChange}
            />
          </div>

          <div className={currentSection === "evaluation" ? "block" : "hidden"}>
            <EvaluationPlaceholder />
          </div>
        </div>
      </div>
    </main>
  );
}
