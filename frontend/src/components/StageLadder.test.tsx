import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StageLadder from "./StageLadder";

describe("StageLadder", () => {
  it("renders all six F2T2EA stage labels", () => {
    render(<StageLadder current="find" />);
    for (const label of ["FIND", "FIX", "TRACK", "TARGET", "ENGAGE", "ASSESS"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("sets an accessible label reflecting the current stage", () => {
    render(<StageLadder current="target" />);
    expect(screen.getByRole("img", { name: /F2T2EA stage: target/i })).toBeInTheDocument();
  });

  it("marks the current stage's label distinctly from later, unreached stages", () => {
    render(<StageLadder current="fix" />);

    const fixLabel = screen.getByText("FIX");
    const targetLabel = screen.getByText("TARGET");

    // The current stage uses the "reached" text color; a stage that
    // hasn't happened yet uses the muted color — these must differ.
    expect(fixLabel.className).not.toBe(targetLabel.className);
    expect(fixLabel.className).toContain("text-console-text");
    expect(targetLabel.className).toContain("text-console-muted");
  });

  it("marks an earlier, already-passed stage as reached too", () => {
    render(<StageLadder current="track" />);
    const findLabel = screen.getByText("FIND");
    // FIND has already happened by the time we're at TRACK, so its label
    // should not be styled as unreached (muted).
    expect(findLabel.className).not.toContain("text-console-muted");
  });
});
