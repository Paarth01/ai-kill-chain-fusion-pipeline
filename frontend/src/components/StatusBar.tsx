import type { EWStatus, SourceType } from "../types";

const SOURCE_LABELS: Record<SourceType, string> = {
  vehicle_ir: "VEHICLE/IR",
  uav_uas: "UAV/UAS",
  elint: "ELINT",
  legacy_c2: "LEGACY C2",
};

interface Props {
  connected: boolean;
  ewStatus: EWStatus | null;
  ewSpoofStatus: EWStatus | null;
  trackCount: number;
  onToggleEW: (source: SourceType) => void;
  onToggleEWSpoof: (source: SourceType) => void;
}

export default function StatusBar({
  connected,
  ewStatus,
  ewSpoofStatus,
  trackCount,
  onToggleEW,
  onToggleEWSpoof,
}: Props) {
  return (
    <header className="border-b border-console-border bg-console-panel px-6 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span
            className={`h-2 w-2 rounded-full ${connected ? "bg-console-good animate-pulse" : "bg-console-critical"}`}
            aria-hidden
          />
          <h1 className="font-mono text-sm tracking-[0.2em] text-console-text">SENTINEL-FFT2EA</h1>
          <span className="text-xs font-mono text-console-muted">
            {connected ? "LIVE FEED" : "CONNECTION LOST"}
          </span>
          <span className="text-xs font-mono text-console-muted">// {trackCount} ACTIVE TRACKS</span>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-console-muted mr-1">EW JAM:</span>
            {ewStatus &&
              (Object.keys(ewStatus) as SourceType[]).map((source) => {
                const degraded = ewStatus[source];
                return (
                  <button
                    key={source}
                    onClick={() => onToggleEW(source)}
                    className={`focus-ring rounded border px-2 py-1 text-[10px] font-mono tracking-wide transition-colors ${
                      degraded
                        ? "border-console-critical text-console-critical bg-console-critical/10"
                        : "border-console-border text-console-muted hover:border-console-good hover:text-console-good"
                    }`}
                    aria-pressed={degraded}
                  >
                    {SOURCE_LABELS[source]}
                  </button>
                );
              })}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-console-muted mr-1">EW SPOOF:</span>
            {ewSpoofStatus &&
              (Object.keys(ewSpoofStatus) as SourceType[]).map((source) => {
                const spoofing = ewSpoofStatus[source];
                return (
                  <button
                    key={source}
                    onClick={() => onToggleEWSpoof(source)}
                    className={`focus-ring rounded border px-2 py-1 text-[10px] font-mono tracking-wide transition-colors ${
                      spoofing
                        ? "border-console-warn text-console-warn bg-console-warn/10"
                        : "border-console-border text-console-muted hover:border-console-good hover:text-console-good"
                    }`}
                    aria-pressed={spoofing}
                  >
                    {SOURCE_LABELS[source]}
                  </button>
                );
              })}
          </div>
        </div>
      </div>
    </header>
  );
}
