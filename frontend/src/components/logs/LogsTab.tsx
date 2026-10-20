import { useEffect, useState } from "react";
import type { LogEntry } from "../../types/log";
import { formatTimeAgo } from "../../utils/time";

const CONTAINER_CLASS = "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm w-full";
const HEADER_CLASS = "p-4 border-b border-slate-800 flex items-center justify-between";
const TITLE_CLASS = "text-base font-semibold text-white";
const COUNT_BADGE_CLASS = "text-xs bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded-full font-mono";
const CLEAR_BTN_CLASS = "text-xs text-slate-400 hover:text-red-400 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 hover:border-red-900/50 transition-colors cursor-pointer";
const EMPTY_STATE_CLASS = "py-20 text-center text-slate-400 text-sm";
const LIST_CONTAINER_CLASS = "divide-y divide-slate-800/70";
const ENTRY_ITEM_CLASS = "p-4 hover:bg-slate-800/30 transition-colors";
const ENTRY_HEADER_CLASS = "flex flex-wrap items-center justify-between gap-2";
const LEVEL_BADGE_ERROR_CLASS = "px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-red-500/20 text-red-400 border border-red-500/30";
const LEVEL_BADGE_WARN_CLASS = "px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-amber-500/20 text-amber-400 border border-amber-500/30";
const LEVEL_BADGE_INFO_CLASS = "px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-sky-500/20 text-sky-400 border border-sky-500/30";
const MESSAGE_BOX_CLASS = "mt-2.5 bg-red-950/30 border border-red-900/50 text-red-200 text-sm px-3 py-2 rounded-lg font-mono";
const DETAILS_CONTAINER_CLASS = "mt-3 pt-3 border-t border-slate-800/60";
const DETAILS_HEADING_CLASS = "text-xs font-medium uppercase tracking-wider text-slate-400 mb-2";
const DETAILS_GRID_CLASS = "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 text-xs";
const DETAIL_CARD_CLASS = "bg-slate-950/70 border border-slate-800 rounded p-2";
const DETAIL_LABEL_CLASS = "text-slate-400 block text-[11px] capitalize";

function getLevelBadgeClass(level: string): string {
  if (level === "error") return LEVEL_BADGE_ERROR_CLASS;
  if (level === "warn") return LEVEL_BADGE_WARN_CLASS;
  return LEVEL_BADGE_INFO_CLASS;
}

type LogsTabProps = {
  logs: LogEntry[];
  onClearLogs: () => void;
};

export function LogsTab({ logs, onClearLogs }: LogsTabProps) {
  const [, setTick] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setTick((t) => t + 1);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={CONTAINER_CLASS}>
      <div className={HEADER_CLASS}>
        <div className="flex items-center gap-3">
          <h2 className={TITLE_CLASS}>Event Log</h2>
          <span className={COUNT_BADGE_CLASS}>
            {logs.length} {logs.length === 1 ? "entry" : "entries"}
          </span>
        </div>
        {logs.length > 0 && (
          <button
            type="button"
            onClick={onClearLogs}
            className={CLEAR_BTN_CLASS}
          >
            Clear logs
          </button>
        )}
      </div>

      {logs.length === 0 ? (
        <div className={EMPTY_STATE_CLASS}>
          No logs yet. System events and errors will appear here.
        </div>
      ) : (
        <div className={LIST_CONTAINER_CLASS}>
          {logs.map((log) => (
            <div key={log.id} className={ENTRY_ITEM_CLASS}>
              <div className={ENTRY_HEADER_CLASS}>
                <div className="flex items-center gap-2">
                  <span className={getLevelBadgeClass(log.level)}>
                    {log.level}
                  </span>
                  <span className="font-medium text-slate-200 text-sm">
                    {log.title}
                  </span>
                </div>
                <div className="text-xs text-slate-400 flex items-center gap-1.5 font-mono">
                  <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className="text-slate-500">
                    ({formatTimeAgo(log.timestamp)})
                  </span>
                </div>
              </div>

              <div className={MESSAGE_BOX_CLASS}>
                {log.message}
              </div>

              {log.details && (
                <div className={DETAILS_CONTAINER_CLASS}>
                  <div className={DETAILS_HEADING_CLASS}>
                    Details
                  </div>
                  <div className={DETAILS_GRID_CLASS}>
                    {Object.entries(log.details).map(([key, value]) => (
                      <div key={key} className={DETAIL_CARD_CLASS}>
                        <span className={DETAIL_LABEL_CLASS}>
                          {key.replace(/_/g, " ")}:
                        </span>
                        <span
                          className={`font-mono break-all ${
                            key === "nip"
                              ? "text-emerald-400 font-medium"
                              : "text-slate-200"
                          }`}
                        >
                          {value !== null && value !== undefined && value !== ""
                            ? String(value)
                            : "—"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
