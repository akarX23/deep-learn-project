import { config } from "../config";
import type { Quiz, SubmittedAnswer } from "../schemas";

interface SubmitChatRequestArgs {
  userPrompt: string;
  sid: string;
  userLevel?: string[];
  files?: File[];
}

interface SubmitQuizRequestArgs {
  sid: string;
  userPrompt: string;
  teachingMaterial: string;
}

interface SubmitQuizEvaluateRequestArgs {
  sid: string;
  quiz: Quiz;
  answers: SubmittedAnswer[];
}

export async function submitChatRequest({
  userPrompt,
  sid,
  userLevel = [],
  files = []
}: SubmitChatRequestArgs): Promise<void> {
  const formData = new FormData();
  formData.append("user_prompt", userPrompt);
  formData.append("sid", sid);

  userLevel.forEach((level) => {
    formData.append("user_level", level);
  });

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${config.apiBaseUrl}/api/chat/request`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to submit chat request");
  }
}

export async function submitQuizRequest({
  sid,
  userPrompt,
  teachingMaterial
}: SubmitQuizRequestArgs): Promise<void> {
  const response = await fetch(`${config.apiBaseUrl}/api/quiz/request`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      sid,
      user_prompt: userPrompt,
      teaching_material: teachingMaterial
    })
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to submit quiz request");
  }
}

export async function submitQuizEvaluateRequest({
  sid,
  quiz,
  answers
}: SubmitQuizEvaluateRequestArgs): Promise<void> {
  const response = await fetch(`${config.apiBaseUrl}/api/quiz/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      sid,
      quiz,
      answers
    })
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Failed to submit quiz evaluation request");
  }
}
