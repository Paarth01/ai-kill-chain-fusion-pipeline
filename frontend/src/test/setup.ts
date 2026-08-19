import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Without vitest's `globals: true`, @testing-library/react can't
// auto-detect a global afterEach to register its DOM cleanup, so it has
// to be wired up explicitly here — otherwise each test file's later
// tests see elements left over from earlier renders in the same file.
afterEach(() => {
  cleanup();
});
