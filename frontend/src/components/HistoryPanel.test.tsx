import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithI18n } from "../test/render";
import { HistoryPanel } from "./HistoryPanel";
import type { HistoryItem } from "../types";

const items: HistoryItem[] = [
  {
    id: 1,
    target_value: "example.com",
    target_type: "domain",
    created_at: "2024-01-01T12:00:00Z",
    total_findings: 7,
  },
];

describe("HistoryPanel", () => {
  it("shows the empty state with no history", () => {
    renderWithI18n(
      <HistoryPanel history={[]} onOpen={vi.fn()} onRefresh={vi.fn()} />,
    );
    expect(screen.getByText(/no saved scans/i)).toBeInTheDocument();
  });

  it("lists history items and opens one on click", async () => {
    const onOpen = vi.fn();
    renderWithI18n(
      <HistoryPanel history={items} onOpen={onOpen} onRefresh={vi.fn()} />,
    );
    await userEvent.click(screen.getByText("example.com"));
    expect(onOpen).toHaveBeenCalledWith(items[0]);
  });

  it("calls onRefresh when Refresh is clicked", async () => {
    const onRefresh = vi.fn();
    renderWithI18n(
      <HistoryPanel history={[]} onOpen={vi.fn()} onRefresh={onRefresh} />,
    );
    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));
    expect(onRefresh).toHaveBeenCalled();
  });
})
