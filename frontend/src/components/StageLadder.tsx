import type { F2T2EAStage } from "../types";

const STAGES: { key: F2T2EAStage; label: string }[] = [
  { key: "find", label: "FIND" },
  { key: "fix", label: "FIX" },
  { key: "track", label: "TRACK" },
  { key: "target", label: "TARGET" },
  { key: "engage", label: "ENGAGE" },
  { key: "assess", label: "ASSESS" },
];

function stageColor(stage: F2T2EAStage): string {
  switch (stage) {
    case "find":
    case "fix":
      return "bg-console-info";
    case "track":
      return "bg-console-good";
    case "target":
      return "bg-console-warn";
    case "engage":
      return "bg-console-critical";
    case "assess":
      return "bg-console-muted";
  }
}

export default function StageLadder({ current }: { current: F2T2EAStage }) {
  const currentIndex = STAGES.findIndex((s) => s.key === current);

  return (
    <div className="flex items-center gap-0.5 w-full" role="img" aria-label={`F2T2EA stage: ${current}`}>
      {STAGES.map((stage, i) => {
        const reached = i <= currentIndex;
        const isCurrent = i === currentIndex;
        return (
          <div key={stage.key} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`h-1.5 w-full rounded-sm transition-all duration-500 ${
                reached ? stageColor(current) : "bg-console-border"
              } ${isCurrent ? "shadow-glowWarn" : ""}`}
            />
            <span
              className={`text-[9px] font-mono tracking-wider ${
                reached ? "text-console-text" : "text-console-muted"
              }`}
            >
              {stage.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
