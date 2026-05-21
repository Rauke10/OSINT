import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Unmount React trees between tests (we do not enable Vitest globals).
afterEach(() => {
  cleanup();
});
