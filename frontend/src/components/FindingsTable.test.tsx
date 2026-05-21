import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithI18n } from "../test/render";
import { FindingsTable } from "./FindingsTable";
import type { Finding } from "../types";

function makeFindings(n: number): Finding[] {
  return Array.from({ length: n }, (_, i) => ({
    source: "crtsh",
    target: "example.com",
    timestamp: "2024-01-01T00:00:00Z",
    confidence: "high" as const,
    kind: "subdomain",
    value: `host${i}.example.com`,
    normalized_data: {},
    graph_node_hint: null,
    pivot_target: null,
  }));
}

function mkFinding(over: Partial<Finding> = {}): Finding {
  return {
    source: "crtsh",
    target: "example.com",
    timestamp: "2024-01-01T00:00:00Z",
    confidence: "high",
    kind: "subdomain",
    value: "host.example.com",
    normalized_data: {},
    graph_node_hint: null,
    pivot_target: null,
    ...over,
  };
}

describe("FindingsTable", () => {
  it("shows an empty state when there are no findings", () => {
    renderWithI18n(<FindingsTable findings={[]} />);
    expect(screen.getByText(/no matching findings/i)).toBeInTheDocument();
  });

  it("renders findings", () => {
    renderWithI18n(<FindingsTable findings={makeFindings(3)} />);
    expect(screen.getByText("host0.example.com")).toBeInTheDocument();
    expect(screen.getByText("host2.example.com")).toBeInTheDocument();
  });

  it("filters findings by the search box", async () => {
    renderWithI18n(<FindingsTable findings={makeFindings(6)} />);
    await userEvent.type(screen.getByPlaceholderText(/filter/i), "host4");
    expect(screen.getByText("host4.example.com")).toBeInTheDocument();
    expect(screen.queryByText("host0.example.com")).not.toBeInTheDocument();
  });

  it("paginates beyond the page size", async () => {
    renderWithI18n(<FindingsTable findings={makeFindings(60)} />);
    expect(screen.queryByText("host55.example.com")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText("host55.example.com")).toBeInTheDocument();
  });

  it("groups findings by value and merges their sources", async () => {
    const findings = [
      mkFinding({ source: "crtsh", value: "api.example.com", confidence: "low" }),
      mkFinding({ source: "otx", value: "api.example.com", confidence: "high" }),
      mkFinding({ source: "crtsh", value: "api.example.com", confidence: "medium" }),
      mkFinding({ source: "crtsh", value: "dev.example.com", confidence: "low" }),
    ];
    renderWithI18n(<FindingsTable findings={findings} />);
    await userEvent.click(screen.getByLabelText(/group by value/i));
    expect(screen.getByText("crtsh, otx")).toBeInTheDocument();
    expect(screen.getByText("api.example.com")).toBeInTheDocument();
    expect(screen.getByText("dev.example.com")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });
});
