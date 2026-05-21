import type { ReactElement } from "react";
import { render, type RenderResult } from "@testing-library/react";
import { I18nProvider } from "../i18n";

/** Render a component tree wrapped in the i18n provider. */
export function renderWithI18n(ui: ReactElement): RenderResult {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

/** Minimal fetch-Response stand-in for tests (jsdom has no fetch). */
export function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
    blob: async () => new Blob([JSON.stringify(body)]),
  } as unknown as Response;
}
