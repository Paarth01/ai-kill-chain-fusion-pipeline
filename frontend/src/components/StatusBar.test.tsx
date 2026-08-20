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

const ewSpoofStatus: EWStatus = {
  vehicle_ir: false,
  uav_uas: false,
  elint: true,
  legacy_c2: false,
};

describe("StatusBar", () => {
  it("shows the live track count", () => {
    render(
      <StatusBar
        connected={true}
        ewStatus={ewStatus}
        ewSpoofStatus={ewSpoofStatus}
        trackCount={7}
        onToggleEW={vi.fn()}
        onToggleEWSpoof={vi.fn()}
      />
    );
    expect(screen.getByText(/7 ACTIVE TRACKS/i)).toBeInTheDocument();
  });

  it("shows LIVE FEED when connected and CONNECTION LOST when not", () => {
    const { rerender } = render(
      <StatusBar
        connected={true}
        ewStatus={ewStatus}
        ewSpoofStatus={ewSpoofStatus}
        trackCount={0}
        onToggleEW={vi.fn()}
        onToggleEWSpoof={vi.fn()}
      />
    );
    expect(screen.getByText("LIVE FEED")).toBeInTheDocument();

    rerender(
      <StatusBar
        connected={false}
        ewStatus={ewStatus}
        ewSpoofStatus={ewSpoofStatus}
        trackCount={0}
        onToggleEW={vi.fn()}
        onToggleEWSpoof={vi.fn()}
      />
    );
    expect(screen.getByText("CONNECTION LOST")).toBeInTheDocument();
  });

  it("marks a degraded source's jam toggle button as pressed", () => {
    render(
      <StatusBar
        connected={true}
        ewStatus={ewStatus}
        ewSpoofStatus={ewSpoofStatus}
        trackCount={0}
        onToggleEW={vi.fn()}
        onToggleEWSpoof={vi.fn()}
      />
    );
    const jamButtons = screen.getAllByText("UAV/UAS");
    expect(jamButtons[0]).toHaveAttribute("aria-pressed", "true");

    const irButtons = screen.getAllByText("VEHICLE/IR");
    expect(irButtons[0]).toHaveAttribute("aria-pressed", "false");
  });

  it("marks a spoofing source's spoof toggle button as pressed, independently of jam state", () => {
    render(
      <StatusBar
        connected={true}
        ewStatus={ewStatus}
        ewSpoofStatus={ewSpoofStatus}
        trackCount={0}
        onToggleEW={vi.fn()}
        onToggleEWSpoof={vi.fn()}
      />
    );
    // ELINT is spoofing but not jammed — both button sets exist (one per
    // section) so grab the second occurrence (spoof section).
    const elintButtons = screen.getAllByText("ELINT");
    expect(elintButtons[1]).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onToggleEW with the correct source type when a jam button is clicked", () => {
    const onToggleEW = vi.fn();
    render(
      <StatusBar
        connected={true}
        ewStatus={ewStatus}
        ewSpoofStatus={ewSpoofStatus}
        trackCount={0}
        onToggleEW={onToggleEW}
        onToggleEWSpoof={vi.fn()}
      />
    );

    fireEvent.click(screen.getAllByText("ELINT")[0]);

    expect(onToggleEW).toHaveBeenCalledWith("elint");
  });

  it("calls onToggleEWSpoof with the correct source type when a spoof button is clicked", () => {
    const onToggleEWSpoof = vi.fn();
    render(
      <StatusBar
        connected={true}
        ewStatus={ewStatus}
        ewSpoofStatus={ewSpoofStatus}
        trackCount={0}
        onToggleEW={vi.fn()}
        onToggleEWSpoof={onToggleEWSpoof}
      />
    );

    fireEvent.click(screen.getAllByText("LEGACY C2")[1]);

    expect(onToggleEWSpoof).toHaveBeenCalledWith("legacy_c2");
  });
});
