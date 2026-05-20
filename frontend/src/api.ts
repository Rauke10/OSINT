import type { HistoryItem, ScanResult, SourceInfo } from "./types";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parse<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = "";
    try {
      detail = ((await r.json()) as { detail?: string }).detail ?? "";
    } catch {
      detail = "";
    }
    throw new ApiError(r.status, detail);
  }
  return (await r.json()) as T;
}

export function getSources(): Promise<SourceInfo[]> {
  return fetch("/api/sources").then((r) => parse<SourceInfo[]>(r));
}

export function runScan(
  target: string,
  pivot: boolean,
  apiKey: string,
): Promise<ScanResult> {
  return fetch("/api/scan", {
    method: "POST",
    headers: { "content-type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify({ target, pivot }),
  }).then((r) => parse<ScanResult>(r));
}

export function getHistory(apiKey: string): Promise<HistoryItem[]> {
  return fetch("/api/history", { headers: { "X-API-Key": apiKey } }).then((r) =>
    parse<HistoryItem[]>(r),
  );
}

export function getHistoryItem(id: number, apiKey: string): Promise<ScanResult> {
  return fetch(`/api/history/${id}`, {
    headers: { "X-API-Key": apiKey },
  }).then((r) => parse<ScanResult>(r));
}

export async function fetchReport(id: number, apiKey: string): Promise<Blob> {
  const r = await fetch(`/api/scan/${id}/report`, {
    headers: { "X-API-Key": apiKey },
  });
  if (!r.ok) throw new ApiError(r.status, "report unavailable");
  return r.blob();
}
