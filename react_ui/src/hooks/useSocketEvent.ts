import { useEffect } from "react";
import { getSocket } from "../services/socket";

export function useSocketEvent<T>(eventName: string, handler: (payload: T) => void): void {
  useEffect(() => {
    const socket = getSocket();
    socket.on(eventName, handler as (...args: unknown[]) => void);

    return () => {
      socket.off(eventName, handler as (...args: unknown[]) => void);
    };
  }, [eventName, handler]);
}
