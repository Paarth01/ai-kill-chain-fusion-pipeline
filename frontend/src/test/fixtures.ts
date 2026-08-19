import type { FusedTrack } from "../types";

export function makeTrack(overrides: Partial<FusedTrack> = {}): FusedTrack {
  return {
    track_id: "TRK-TEST1234",
    coordinates: { lat: 28.6, lon: 77.2 },
    contributing_sources: ["vehicle_ir"],
    reading_count: 1,
    confidence: 0.6,
    severity: "unknown",
    stage: "find",
    stage_history: ["find"],
    first_seen: new Date().toISOString(),
    last_updated: new Date().toISOString(),
    operator_ack: false,
    degraded: false,
    ...overrides,
  };
}
