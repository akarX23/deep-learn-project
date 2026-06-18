import { useEffect, useMemo, useState } from "react";
import { ChatWindow } from "./components/Chat/ChatWindow";
import { EvaluationPlaceholder } from "./components/Evaluation/EvaluationPlaceholder";
import { Navbar } from "./components/Navbar";
import { Navigation } from "./components/Navigation";
import { QuizPlaceholder } from "./components/Quiz/QuizPlaceholder";
import { submitChatRequest } from "./services/api";
import { getSocket } from "./services/socket";
import { uiClasses } from "./styles/uiClasses";

type Section = "chat" | "quiz" | "evaluation";

export default function App(): JSX.Element {
  const [currentSection, setCurrentSection] = useState<Section>("chat");
  const [socketId, setSocketId] = useState<string | null>(null);

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

  const sectionView = useMemo(() => {
    if (currentSection === "chat") {
      return (
        <ChatWindow
          sid={socketId}
          onSubmitRequest={(prompt, files) =>
            submitChatRequest({
              userPrompt: prompt,
              sid: socketId ?? "",
              userLevel: [],
              files
            })
          }
        />
      );
    }

    if (currentSection === "quiz") {
      return <QuizPlaceholder />;
    }

    return <EvaluationPlaceholder />;
  }, [currentSection, socketId]);

  return (
    <main className={uiClasses.layout.page}>
      <div className={uiClasses.layout.container}>
        <Navbar title="AI Tutor" />
        <Navigation current={currentSection} onSelect={setCurrentSection} />
        <div className={uiClasses.layout.card}>{sectionView}</div>
      </div>
    </main>
  );
}
