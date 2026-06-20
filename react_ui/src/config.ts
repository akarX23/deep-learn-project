function mustEnv(name: string): string {
  const value = import.meta.env[name] as string | undefined;
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const config = {
  apiBaseUrl: mustEnv("VITE_API_BASE_URL"),
  wsUrl: mustEnv("VITE_WS_URL")
};
