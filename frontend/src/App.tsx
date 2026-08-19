import { useCallback, useEffect, useState } from "react";
import StatusBar from "./components/StatusBar";
import TrackCard from "./components/TrackCard";
import TrackMap from "./components/TrackMap";
import { acknowledgeTrack, assessTrack, subscribeToTrackStream, toggleEW } from "./api";
import type { EWStatus, FusedTrack, SourceType } from "./types";

type ViewMode = "grid" | "map";

export default function App() {
  const [tracks, setTracks] = useState<FusedTrack[]>([]);
  const [ewStatus, setEwStatus] = useState<EWStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const [view, setView] = useState<ViewMode>("grid");

  useEffect(() => {
    const unsubscribe = subscribeToTrackStream(
      (payload) => {
        setConnected(true);
        setTracks(payload.tracks);
        setEwStatus(payload.ew_status);
      },
      () => setConnected(false)
    );
    return unsubscribe;
  }, []);

  const handleToggleEW = useCallback(async (source: SourceType) => {
    await toggleEW(source);
  }, []);

  const handleAck = useCallback(async (id: string) => {
    await acknowledgeTrack(id);
  }, []);

  const handleAssess = useCallback(async (id: string, summary: string) => {
    await assessTrack(id, summary);
  }, []);

  const sortedTracks = [...tracks].sort((a, b) => {
    const order = ["target", "engage", "track", "fix", "find", "assess"];
    return order.indexOf(a.stage) - order.indexOf(b.stage);
  });

  return (
    <div className="min-h-screen bg-console-bg text-console-text">
      <StatusBar
        connected={connected}
        ewStatus={ewStatus}
        trackCount={tracks.length}
        onToggleEW={handleToggleEW}
      />

      <main className="p-6">
        {sortedTracks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <p className="font-mono text-sm text-console-muted">
              {connected ? "NO ACTIVE TRACKS — awaiting first fused contact" : "Connecting to fusion feed..."}
            </p>
          </div>
        ) : (
          <>
            <div className="mb-4 flex gap-2">
              {(["grid", "map"] as ViewMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setView(mode)}
                  className={`focus-ring rounded border px-3 py-1 text-[11px] font-mono uppercase tracking-wider transition-colors ${
                    view === mode
                      ? "border-console-good text-console-good bg-console-good/10"
                      : "border-console-border text-console-muted hover:text-console-text"
                  }`}
                  aria-pressed={view === mode}
                >
                  {mode}
                </button>
              ))}
            </div>

            {view === "map" ? (
              <TrackMap tracks={sortedTracks} />
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {sortedTracks.map((track) => (
                  <TrackCard key={track.track_id} track={track} onAck={handleAck} onAssess={handleAssess} />
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
