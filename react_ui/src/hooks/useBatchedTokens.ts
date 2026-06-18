import { useCallback, useEffect, useRef, useState } from "react";

export function useBatchedTokens(delayMs = 100): {
  streamedText: string;
  addToken: (token: string) => void;
  reset: () => void;
} {
  const [streamedText, setStreamedText] = useState("");
  const bufferRef = useRef("");
  const timerRef = useRef<number | null>(null);

  const flush = useCallback(() => {
    if (!bufferRef.current) {
      return;
    }

    setStreamedText((prev) => prev + bufferRef.current);
    bufferRef.current = "";
    timerRef.current = null;
  }, []);

  const addToken = useCallback(
    (token: string) => {
      bufferRef.current += token;
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
      timerRef.current = window.setTimeout(flush, delayMs);
    },
    [delayMs, flush]
  );

  const reset = useCallback(() => {
    bufferRef.current = "";
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setStreamedText("");
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  return { streamedText, addToken, reset };
}
