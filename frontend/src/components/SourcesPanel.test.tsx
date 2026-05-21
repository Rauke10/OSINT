import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithI18n } from "../test/render";
import { SourcesPanel } from "./SourcesPanel";
import type { ScanResult, SourceInfo } from "../types";

const result: ScanResult = {
  target: { raw: "example.com", type: "domain", value: "example.com" },
  summary: {
    duration_seconds: 1,
    sources_used: ["crtsh"],
    sources_skipped: { shodan: "missing API key" },
    findings: { low: 0, medium: 0, high: 1, total: 1 },
    pivoted_targets: [],
  },
  findings: [
    {
      source: "crtsh",
      target: "example.com",
      timestamp: "2024-01-01T00:00:00Z",
      confidence: "high",
      kind: "subdomain",
      value: "api.example.com",
      normalized_data: {},
      graph_node_hint: null,
      pivot_target: null,
    },
  ],
};

const catalog: SourceInfo[] = [
  {
    name: "crtsh",
    label: "crt.sh",
    description: "CT logs",
    requires_api_key: false,
    available: true,
    targets: ["domain"],
  },
  {
    name: "shodan",
    label: "Shodan",
    description: "Services",
    requires_api_key: true,
    available: false,
    targets: ["ip"],
  },
];

describe("SourcesPanel", () => {
  it("lists used and skipped sources with their reasons", () => {
    renderWithI18n(<SourcesPanel result={result} catalog={catalog} />);
    expect(screen.getByText("crt.sh")).toBeInTheDocument();
    expect(screen.getByText("Shodan")).toBeInTheDocument();
    expect(screen.getByText("missing API key")).toBeInTheDocument();
  });

  it("counts findings per used source", () => {
    renderWithI18n(<SourcesPanel result={result} catalog={catalog} />);
    // crt.sh contributed exactly one finding.
    expect(screen.getByText("1")).toBeInTheDocument();
  });
})
