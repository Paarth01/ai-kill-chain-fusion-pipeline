export type SourceType = "vehicle_ir" | "uav_uas" | "elint" | "legacy_c2";

export type ThreatSeverity = "unknown" | "low" | "medium" | "high";

export type F2T2EAStage = "find" | "fix" | "track" | "target" | "engage" | "assess";

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface FusedTrack {
  track_id: string;
  coordinates: Coordinates;
  contributing_sources: SourceType[];
  reading_count: number;
  confidence: number;
  severity: ThreatSeverity;
  stage: F2T2EAStage;
  stage_history: F2T2EAStage[];
  first_seen: string;
  last_updated: string;
  operator_ack: boolean;
  degraded: boolean;
}

export interface EWStatus {
  vehicle_ir: boolean;
  uav_uas: boolean;
  elint: boolean;
  legacy_c2: boolean;
}

export interface TracksUpdatePayload {
  tracks: FusedTrack[];
  ew_status: EWStatus;
  ew_spoof_status: EWStatus;
}

export interface StageEvent {
  track_id: string;
  stage: F2T2EAStage;
  severity: ThreatSeverity;
  confidence: number;
  contributing_sources: SourceType[];
  timestamp: string;
}
