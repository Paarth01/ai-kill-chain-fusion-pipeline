import { useState } from "react";
import type { FusedTrack, SourceType } from "../types";
import StageLadder from "./StageLadder";

const SOURCE_SHORT: Record<SourceType, string> = {
  vehicle_ir: "IR",
  uav_uas: "UAV",
  elint: "ELINT",
  legacy_c2: "C2",
};

const SEVERITY_STYLES: Record<string, string> = {
  unknown: "text-console-muted border-console-border",
  low: "text-console-info border-console-info/40",
  medium: "text-console-warn border-console-warn/40",
  high: "text-console-critical border-console-critical/40",
};

interface Props {
  track: FusedTrack;
  onAck: (id: string) => Promise<void>;
  onAssess: (id: string, summary: string) => Promise<void>;
}

export default function TrackCard({ track, onAck, onAssess }: Props) {
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState("");

  const handleAck = async () => {
    setBusy(true);
    try {
      await onAck(track.track_id);
    } finally {
      setBusy(false);
    }
  };

  const handleAssess = async () => {
    setBusy(true);
    try {
      await onAssess(track.track_id, summary || "closed by operator");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={`rounded-md border bg-console-panelRaised p-4 flex flex-col gap-3 transition-shadow ${
        track.degraded ? "border-console-critical/50" : "border-console-border"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-console-text tracking-wide">{track.track_id}</span>
        <span
          className={`rounded border px-2 py-0.5 text-[10px] font-mono uppercase ${SEVERITY_STYLES[track.severity]}`}
        >
          {track.severity}
        </span>
      </div>

      <StageLadder current={track.stage} />

      <div className="flex items-center justify-between text-[11px] font-mono text-console-muted">
        <span>
          {track.coordinates.lat.toFixed(4)}, {track.coordinates.lon.toFixed(4)}
        </span>
        <span>{track.reading_count} reports</span>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 rounded-full bg-console-border overflow-hidden">
          <div
            className="h-full bg-console-good transition-all duration-500"
            style={{ width: `${Math.round(track.confidence * 100)}%` }}
          />
        </div>
        <span className="text-[10px] font-mono text-console-muted w-9 text-right">
          {Math.round(track.confidence * 100)}%
        </span>
      </div>

      <div className="flex flex-wrap gap-1">
        {track.contributing_sources.map((s, i) => (
          <span
            key={`${s}-${i}`}
            className="rounded bg-console-bg border border-console-border px-1.5 py-0.5 text-[9px] font-mono text-console-muted"
          >
            {SOURCE_SHORT[s]}
          </span>
        ))}
        {track.degraded && (
          <span className="rounded border border-console-critical/50 px-1.5 py-0.5 text-[9px] font-mono text-console-critical">
            DEGRADED
          </span>
        )}
      </div>

      {track.stage === "target" && (
        <button
          onClick={handleAck}
          disabled={busy}
          className="focus-ring mt-1 rounded border border-console-critical/60 bg-console-critical/10 py-1.5 text-[11px] font-mono tracking-wide text-console-critical hover:bg-console-critical/20 disabled:opacity-50"
        >
          ACKNOWLEDGE → ENGAGE
        </button>
      )}

      {track.stage === "engage" && (
        <div className="flex gap-2">
          <input
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Outcome summary..."
            className="focus-ring flex-1 rounded border border-console-border bg-console-bg px-2 py-1 text-[11px] font-mono text-console-text placeholder:text-console-muted"
          />
          <button
            onClick={handleAssess}
            disabled={busy}
            className="focus-ring rounded border border-console-muted/60 px-3 text-[11px] font-mono text-console-muted hover:text-console-text disabled:opacity-50"
          >
            CLOSE OUT
          </button>
        </div>
      )}
    </div>
  );
}
