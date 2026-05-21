import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { renderWithI18n } from "./test/render";
import { jsonResponse } from "./test/render";

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  document.documentElement.className = "";
  // App fetches /api/sources on mount; keep it inert.
  vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, [])));
});

describe("App", () => {
  it("renders the header and the scan form", () => {
    renderWithI18n(<App />);
    expect(screen.getByText("GLOBEYE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /scan/i })).toBeInTheDocument();
  });

  it("toggles the colour theme", async () => {
    renderWithI18n(<App />);
    await waitFor(() =>
      expect(document.documentElement).toHaveClass("dark"),
    );
    await userEvent.click(screen.getByRole("button", { name: /theme/i }));
    await waitFor(() =>
      expect(document.documentElement).not.toHaveClass("dark"),
    );
  });

  it("stores the API key in sessionStorage by default", async () => {
    renderWithI18n(<App />);
    await userEvent.type(screen.getByPlaceholderText("X-API-Key"), "secret");
    expect(sessionStorage.getItem("globeye-key")).toBe("secret");
    expect(localStorage.getItem("globeye-key")).toBeNull();
  });

  it("stores the API key in localStorage once 'remember' is on", async () => {
    renderWithI18n(<App />);
    await userEvent.click(
      screen.getByRole("checkbox", { name: /remember/i }),
    );
    await userEvent.type(screen.getByPlaceholderText("X-API-Key"), "k");
    expect(localStorage.getItem("globeye-key")).toBe("k");
  });

  it("switches the UI language", async () => {
    renderWithI18n(<App />);
    await userEvent.click(screen.getByRole("button", { name: "ES" }));
    expect(screen.getByRole("button", { name: /escanear/i })).toBeInTheDocument();
  });
});
