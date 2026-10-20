export type LogLevel = "error" | "info" | "warn";

export type LogEntry = {
  id: string;
  timestamp: string;
  level: LogLevel;
  title: string;
  message: string;
  details?: Record<string, unknown>;
};
