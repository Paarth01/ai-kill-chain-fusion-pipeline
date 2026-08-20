import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { makeTrack } from "./test/fixtures";
import type { TracksUpdatePayload } from "./types";

// App's own logic — connection state, track sorting, wiring callbacks to
// children — is what this file tests. The SSE transport itself is
// covered in api.test.ts; TrackMap/HistoryPanel's internals have their
// own test files. Mocking ./api here keeps this file testing App's
// logic, not re-testing (or fighting jsdom's lack of a real EventSource
// implementation for) things already covered elsewhere.
const { subscribeToTrackStream, acknowledgeTrack, assessTrack, toggleEW } = vi.hoisted(() => ({
  subscribeToTrackStream: vi.fn(),
  acknowledgeTrack: vi.fn().mockResolvedValue(undefined),
  assessTrack: vi.fn().mockResolvedValue(undefined),
  toggleEW: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("./api", () => ({
  subscribeToTrackStream,
  acknowledgeTrack,
  assessTrack,
  toggleEW,
  fetchRecentHistory: vi.fn().mockResolvedValue([]),
}));

/** Grabs the onUpdate callback App registered with subscribeToTrackStream
 * on its most recent render, so a test can simulate an SSE push. */
function emitStreamUpdate(payload: TracksUpdatePayload) {
  const onUpdate = subscribeToTrackStream.mock.calls[0][0] as (p: TracksUpdatePayload) => void;
  onUpdate(payload);
}

function emitStreamError() {
  const onError = subscribeToTrackStream.mock.calls[0][1] as () => void;
  onError();
}

const ewStatus = { vehicle_ir: false, uav_uas: false, elint: false, legacy_c2: false };

describe("App", () => {
  beforeEach(() => {
    subscribeToTrackStream.mockReset();
    subscribeToTrackStream.mockReturnValue(() => {});
    acknowledgeTrack.mockClear();
  });

  it("shows a connecting message before any SSE data arrives", () => {
    render(<App />);
    expect(screen.getByText(/Connecting to fusion feed/i)).toBeInTheDocument();
  });

  it("shows LIVE FEED and renders tracks once the stream delivers data", async () => {
    render(<App />);

    emitStreamUpdate({
      tracks: [makeTrack({ track_id: "TRK-LIVE0001", stage: "find" })],
      ew_status: ewStatus,
    });

    await waitFor(() => {
      expect(screen.getByText("LIVE FEED")).toBeInTheDocument();
    });
    expect(screen.getByText("TRK-LIVE0001")).toBeInTheDocument();
  });

  it("falls back to CONNECTION LOST if the stream errors", async () => {
    render(<App />);

    emitStreamUpdate({ tracks: [], ew_status: ewStatus });
    await waitFor(() => expect(screen.getByText("LIVE FEED")).toBeInTheDocument());

    emitStreamError();
    await waitFor(() => expect(screen.getByText("CONNECTION LOST")).toBeInTheDocument());
  });

  it("sorts tracks by urgency — target and engage first, assess last", async () => {
    render(<App />);

    emitStreamUpdate({
      tracks: [
        makeTrack({ track_id: "TRK-FIND0001", stage: "find" }),
        makeTrack({ track_id: "TRK-ASSESS01", stage: "assess" }),
        makeTrack({ track_id: "TRK-TARGET01", stage: "target" }),
        makeTrack({ track_id: "TRK-ENGAGE01", stage: "engage" }),
      ],
      ew_status: ewStatus,
    });

    await waitFor(() => expect(screen.getByText("TRK-TARGET01")).toBeInTheDocument());

    const ids = screen.getAllByText(/^TRK-/).map((el) => el.textContent);
    const targetIndex = ids.indexOf("TRK-TARGET01");
    const engageIndex = ids.indexOf("TRK-ENGAGE01");
    const findIndex = ids.indexOf("TRK-FIND0001");
    const assessIndex = ids.indexOf("TRK-ASSESS01");

    expect(targetIndex).toBeLessThan(findIndex);
    expect(engageIndex).toBeLessThan(findIndex);
    expect(findIndex).toBeLessThan(assessIndex);
  });

  it("wires TrackCard's Acknowledge action through to the api module", async () => {
    render(<App />);

    emitStreamUpdate({
      tracks: [makeTrack({ track_id: "TRK-ACKME001", stage: "target" })],
      ew_status: ewStatus,
    });

    await waitFor(() => expect(screen.getByText("TRK-ACKME001")).toBeInTheDocument());
    fireEvent.click(screen.getByText(/ACKNOWLEDGE/i));

    expect(acknowledgeTrack).toHaveBeenCalledWith("TRK-ACKME001");
  });

  it("switches to the History view without requiring any active tracks", async () => {
    render(<App />);

    fireEvent.click(screen.getByText("history"));

    await waitFor(() => {
      expect(screen.getByText(/STAGE TRANSITION LOG/i)).toBeInTheDocument();
    });
  });
});
