import { useEffect, useMemo, useState } from "react";
import { ChatWindow } from "./components/Chat/ChatWindow";
import { EvaluationPlaceholder } from "./components/Evaluation/EvaluationPlaceholder";
import { Navigation } from "./components/Navigation";
import { QuizPlaceholder } from "./components/Quiz/QuizPlaceholder";
import { submitChatRequest } from "./services/api";
import { getSocket } from "./services/socket";

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
    <main
      style={{
        maxWidth: 860,
        margin: "32px auto",
        padding: 16,
        fontFamily: "Segoe UI, Tahoma, sans-serif",
        color: "#111827"
      }}
    >
      <Navigation current={currentSection} onSelect={setCurrentSection} />
      <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 16, background: "#ffffff" }}>
        {sectionView}
      </div>
    </main>
  );
}
