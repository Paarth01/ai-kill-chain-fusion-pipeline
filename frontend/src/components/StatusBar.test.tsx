import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import StatusBar from "./StatusBar";
import type { EWStatus } from "../types";

const ewStatus: EWStatus = {
  vehicle_ir: false,
  uav_uas: true,
  elint: false,
  legacy_c2: false,
};

describe("StatusBar", () => {
  it("shows the live track count", () => {
    render(<StatusBar connected={true} ewStatus={ewStatus} trackCount={7} onToggleEW={vi.fn()} />);
    expect(screen.getByText(/7 ACTIVE TRACKS/i)).toBeInTheDocument();
  });

  it("shows LIVE FEED when connected and CONNECTION LOST when not", () => {
    const { rerender } = render(
      <StatusBar connected={true} ewStatus={ewStatus} trackCount={0} onToggleEW={vi.fn()} />
    );
    expect(screen.getByText("LIVE FEED")).toBeInTheDocument();

    rerender(<StatusBar connected={false} ewStatus={ewStatus} trackCount={0} onToggleEW={vi.fn()} />);
    expect(screen.getByText("CONNECTION LOST")).toBeInTheDocument();
  });

  it("marks a degraded source's toggle button as pressed", () => {
    render(<StatusBar connected={true} ewStatus={ewStatus} trackCount={0} onToggleEW={vi.fn()} />);
    const uavButton = screen.getByText("UAV/UAS");
    expect(uavButton).toHaveAttribute("aria-pressed", "true");

    const irButton = screen.getByText("VEHICLE/IR");
    expect(irButton).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onToggleEW with the correct source type when a button is clicked", () => {
    const onToggleEW = vi.fn();
    render(<StatusBar connected={true} ewStatus={ewStatus} trackCount={0} onToggleEW={onToggleEW} />);

    fireEvent.click(screen.getByText("ELINT"));

    expect(onToggleEW).toHaveBeenCalledWith("elint");
  });
});
