import { useEffect, useRef, useState } from "react";
import { fetchRecentHistory } from "../api";
import type { StageEvent } from "../types";

const STAGE_COLORS: Record<string, string> = {
  find: "text-console-info",
  fix: "text-console-info",
  track: "text-console-good",
  target: "text-console-warn",
  engage: "text-console-critical",
  assess: "text-console-muted",
};

const AUTO_REFRESH_INTERVAL_MS = 5000;

export default function HistoryPanel() {
  const [events, setEvents] = useState<StageEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecentHistory(50);
      setEvents(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(load, AUTO_REFRESH_INTERVAL_MS);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    // Always clean up on unmount or before re-running this effect, so a
    // toggled-off panel (or an unmounted one, e.g. switching views) never
    // leaves a stray interval polling in the background.
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh]);

  return (
    <div className="rounded-md border border-console-border bg-console-panelRaised">
      <div className="flex items-center justify-between border-b border-console-border px-4 py-2">
        <span className="font-mono text-xs tracking-wider text-console-muted">
          STAGE TRANSITION LOG (persistent — survives a restart)
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh((prev) => !prev)}
            aria-pressed={autoRefresh}
            className={`focus-ring rounded border px-2 py-0.5 text-[10px] font-mono tracking-wide transition-colors ${
              autoRefresh
                ? "border-console-good text-console-good bg-console-good/10"
                : "border-console-border text-console-muted hover:text-console-text"
            }`}
          >
            AUTO: {autoRefresh ? "ON" : "OFF"}
          </button>
          <button
            onClick={load}
            disabled={loading}
            className="focus-ring rounded border border-console-border px-2 py-0.5 text-[10px] font-mono text-console-muted hover:text-console-text disabled:opacity-50"
          >
            {loading ? "LOADING…" : "REFRESH"}
          </button>
        </div>
      </div>

      <div className="max-h-[480px] overflow-y-auto">
        {error && <div className="p-4 text-xs font-mono text-console-critical">{error}</div>}

        {!error && events.length === 0 && !loading && (
          <div className="p-4 text-xs font-mono text-console-muted">No stage transitions logged yet.</div>
        )}

        <table className="w-full text-left text-[11px] font-mono">
          <tbody>
            {events.map((event, i) => (
              <tr key={`${event.track_id}-${event.timestamp}-${i}`} className="border-b border-console-border/50">
                <td className="whitespace-nowrap px-4 py-1.5 text-console-muted">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </td>
                <td className="px-2 py-1.5 text-console-text">{event.track_id}</td>
                <td className={`px-2 py-1.5 uppercase ${STAGE_COLORS[event.stage] ?? "text-console-text"}`}>
                  {event.stage}
                </td>
                <td className="px-2 py-1.5 text-console-muted">{Math.round(event.confidence * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
