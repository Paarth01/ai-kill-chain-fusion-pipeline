import { expect, test } from "@playwright/test";

/**
 * Real browser verification against the live stack (backend + frontend
 * dev server both running — see playwright.config.ts and the CI job that
 * drives this). This is the test that answers "does it actually render",
 * not just "does it compile" — component tests (src/components/*.test.tsx)
 * cover logic in isolation; this covers the real SSE-driven integration.
 *
 * Could not be run inside the sandbox this project was built in: that
 * environment's network allowlist blocks every source of a downloadable
 * browser binary (Docker Hub, Playwright's own CDN, and Ubuntu's
 * chromium-browser package is a dead snap stub with no working snapd).
 * GitHub Actions runners don't have that restriction, so this executes
 * for real in CI — check the Actions tab after pushing rather than
 * taking "it's written" as "it's verified".
 */

test("dashboard connects to the live SSE stream and renders track data", async ({ page }) => {
  await page.goto("/");

  // Confirm the connection indicator flips from connecting to live —
  // this only happens if the SSE stream actually delivered a real
  // payload from the backend, not just that the page loaded.
  await expect(page.getByText("LIVE FEED")).toBeVisible({ timeout: 15_000 });

  // With feed intervals sped up in CI, tracks should exist within a few
  // seconds — assert the empty-state message is gone rather than
  // asserting an exact count, since track count is inherently
  // nondeterministic (random synthetic coordinates/timing).
  await expect(page.getByText(/NO ACTIVE TRACKS/i)).not.toBeVisible({ timeout: 15_000 });

  // At least one track card should be rendered with a real track ID.
  await expect(page.getByText(/TRK-[A-F0-9]{8}/i).first()).toBeVisible();
});

test("Grid/Map toggle switches views without losing the connection", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("LIVE FEED")).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: "map", exact: true }).click();

  // Leaflet renders its own canvas/pane structure — confirm the map
  // container actually mounted rather than the button merely toggling
  // React state with nothing to show for it.
  await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 10_000 });

  // Switching back to grid shouldn't have dropped the SSE connection.
  await page.getByRole("button", { name: "grid", exact: true }).click();
  await expect(page.getByText("LIVE FEED")).toBeVisible();
});

test("EW toggle button reflects degraded state after clicking", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("LIVE FEED")).toBeVisible({ timeout: 15_000 });

  // Scoped by aria-label, not visible text — "UAV/UAS" alone is now
  // ambiguous (it also appears in the EW SPOOF toggle row), so this
  // targets the jam toggle specifically. Also makes the test resilient
  // to future additions of more EW-related toggle rows.
  const uavToggle = page.getByRole("button", { name: "EW jam toggle: UAV/UAS" });
  const initialState = await uavToggle.getAttribute("aria-pressed");

  await uavToggle.click();

  // The button's pressed state should flip after the round trip to the
  // backend and the next SSE broadcast reflects it back.
  await expect(uavToggle).toHaveAttribute("aria-pressed", initialState === "true" ? "false" : "true", {
    timeout: 5_000,
  });
});

test("EW spoof toggle button reflects state independently of the jam toggle", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("LIVE FEED")).toBeVisible({ timeout: 15_000 });

  const spoofToggle = page.getByRole("button", { name: "EW spoof toggle: ELINT" });
  const initialState = await spoofToggle.getAttribute("aria-pressed");

  await spoofToggle.click();

  await expect(spoofToggle).toHaveAttribute("aria-pressed", initialState === "true" ? "false" : "true", {
    timeout: 5_000,
  });
});