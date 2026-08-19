import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { makeTrack } from "../test/fixtures";
import TrackCard from "./TrackCard";

describe("TrackCard", () => {
  it("shows the severity badge", () => {
    render(<TrackCard track={makeTrack({ severity: "high" })} onAck={vi.fn()} onAssess={vi.fn()} />);
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("does not show the Acknowledge control outside TARGET stage", () => {
    render(<TrackCard track={makeTrack({ stage: "track" })} onAck={vi.fn()} onAssess={vi.fn()} />);
    expect(screen.queryByText(/ACKNOWLEDGE/i)).not.toBeInTheDocument();
  });

  it("shows the Acknowledge control at TARGET stage and calls onAck with the track id", async () => {
    const onAck = vi.fn().mockResolvedValue(undefined);
    render(<TrackCard track={makeTrack({ track_id: "TRK-ABC999", stage: "target" })} onAck={onAck} onAssess={vi.fn()} />);

    const button = screen.getByText(/ACKNOWLEDGE/i);
    fireEvent.click(button);

    expect(onAck).toHaveBeenCalledWith("TRK-ABC999");
  });

  it("does not show the close-out control outside ENGAGE stage", () => {
    render(<TrackCard track={makeTrack({ stage: "target" })} onAck={vi.fn()} onAssess={vi.fn()} />);
    expect(screen.queryByText(/CLOSE OUT/i)).not.toBeInTheDocument();
  });

  it("shows the close-out control at ENGAGE stage and calls onAssess with the typed summary", () => {
    const onAssess = vi.fn().mockResolvedValue(undefined);
    render(<TrackCard track={makeTrack({ track_id: "TRK-ENG001", stage: "engage" })} onAck={vi.fn()} onAssess={onAssess} />);

    const input = screen.getByPlaceholderText(/Outcome summary/i);
    fireEvent.change(input, { target: { value: "resolved, false alarm" } });
    fireEvent.click(screen.getByText(/CLOSE OUT/i));

    expect(onAssess).toHaveBeenCalledWith("TRK-ENG001", "resolved, false alarm");
  });

  it("shows a DEGRADED indicator when the track is EW-degraded", () => {
    render(<TrackCard track={makeTrack({ degraded: true })} onAck={vi.fn()} onAssess={vi.fn()} />);
    expect(screen.getByText("DEGRADED")).toBeInTheDocument();
  });
});
