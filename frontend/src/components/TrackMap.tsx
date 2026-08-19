import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import type { FusedTrack, ThreatSeverity } from "../types";

const SEVERITY_COLORS: Record<ThreatSeverity, string> = {
  unknown: "#5B6B62",
  low: "#5CC8FF",
  medium: "#F5A623",
  high: "#FF5A4E",
};

// Matches the synthetic coordinate bounding box in
// backend/app/feeds/base.py — centers the map on the same region the
// feeds actually generate contacts in.
const DEFAULT_CENTER: [number, number] = [28.575, 77.15];
const DEFAULT_ZOOM = 11;

export default function TrackMap({ tracks }: { tracks: FusedTrack[] }) {
  return (
    <div className="h-[520px] w-full overflow-hidden rounded-md border border-console-border">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: "100%", width: "100%", background: "#0A0D0B" }}
        preferCanvas
      >
        {/* Dark basemap to match the console aesthetic — free tier, no API key required */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />

        {tracks.map((track) => (
          <CircleMarker
            key={track.track_id}
            center={[track.coordinates.lat, track.coordinates.lon]}
            radius={track.stage === "target" || track.stage === "engage" ? 10 : 7}
            pathOptions={{
              color: SEVERITY_COLORS[track.severity],
              fillColor: SEVERITY_COLORS[track.severity],
              fillOpacity: track.degraded ? 0.25 : 0.55,
              weight: 2,
            }}
          >
            <Popup>
              <div className="font-mono text-xs leading-relaxed">
                <div className="font-semibold">{track.track_id}</div>
                <div>Stage: {track.stage.toUpperCase()}</div>
                <div>Severity: {track.severity.toUpperCase()}</div>
                <div>Confidence: {Math.round(track.confidence * 100)}%</div>
                <div>Sources: {track.contributing_sources.join(", ")}</div>
                {track.degraded && <div className="text-red-600">DEGRADED (EW)</div>}
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
