import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import HistoryPanel from "./HistoryPanel";

describe("HistoryPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("renders fetched history events", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => [
          {
            track_id: "TRK-ABC12345",
            stage: "target",
            severity: "high",
            confidence: 0.82,
            contributing_sources: ["vehicle_ir", "uav_uas"],
            timestamp: new Date().toISOString(),
          },
        ],
      }))
    );

    render(<HistoryPanel />);

    await waitFor(() => {
      expect(screen.getByText("TRK-ABC12345")).toBeInTheDocument();
    });
    expect(screen.getByText("target")).toBeInTheDocument();
  });

  it("shows an empty-state message when there is no history yet", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => [] }))
    );

    render(<HistoryPanel />);

    await waitFor(() => {
      expect(screen.getByText(/No stage transitions logged yet/i)).toBeInTheDocument();
    });
  });

  it("shows an error message when the request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, text: async () => "Internal Server Error" }))
    );

    render(<HistoryPanel />);

    await waitFor(() => {
      expect(screen.getByText("Internal Server Error")).toBeInTheDocument();
    });
  });

  it("does not auto-refresh by default — fetch is called once on mount only", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => [] }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HistoryPanel />);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    await vi.advanceTimersByTimeAsync(20_000);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("polls on an interval once AUTO is toggled on, and stops when toggled back off", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => [] }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HistoryPanel />);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByText(/AUTO: OFF/i));
    await vi.waitFor(() => expect(screen.getByText(/AUTO: ON/i)).toBeInTheDocument());

    await vi.advanceTimersByTimeAsync(5000);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    await vi.advanceTimersByTimeAsync(5000);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    fireEvent.click(screen.getByText(/AUTO: ON/i));
    await vi.waitFor(() => expect(screen.getByText(/AUTO: OFF/i)).toBeInTheDocument());

    const countAfterStop = fetchMock.mock.calls.length;
    await vi.advanceTimersByTimeAsync(15_000);

    // No further calls once auto-refresh is switched back off — proves
    // the interval was actually cleared, not just hidden from the UI.
    expect(fetchMock).toHaveBeenCalledTimes(countAfterStop);
  });
});
