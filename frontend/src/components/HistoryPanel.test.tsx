import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import HistoryPanel from "./HistoryPanel";

describe("HistoryPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
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
});
