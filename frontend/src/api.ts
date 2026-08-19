import type { SourceType, TracksUpdatePayload } from "./types";

// In dev, this is empty and requests go through Vite's proxy (see
// vite.config.ts) to http://localhost:8000. In production, set
// VITE_API_BASE_URL to your deployed backend's origin (e.g. Render) — the
// frontend and backend are typically deployed separately (e.g. Vercel +
// Render), so relative paths alone would resolve against the frontend's
// own origin and silently fail.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function subscribeToTrackStream(onUpdate: (payload: TracksUpdatePayload) => void, onError: () => void) {
  const source = new EventSource(`${API_BASE}/stream/tracks`);

  source.addEventListener("tracks_update", (event) => {
    try {
      const payload: TracksUpdatePayload = JSON.parse((event as MessageEvent).data);
      onUpdate(payload);
    } catch {
      // Ignore malformed frames rather than tearing down the connection.
    }
  });

  source.onerror = () => {
    onError();
  };

  return () => source.close();
}

export async function acknowledgeTrack(trackId: string) {
  const res = await fetch(`${API_BASE}/tracks/${trackId}/ack`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function assessTrack(trackId: string, summary: string) {
  const res = await fetch(`${API_BASE}/tracks/${trackId}/assess?summary=${encodeURIComponent(summary)}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function toggleEW(sourceType: SourceType) {
  const res = await fetch(`${API_BASE}/ew/toggle?source_type=${sourceType}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
