import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  fetchReport,
  getHistory,
  getSources,
  runScan,
} from "./api";
import { jsonResponse } from "./test/render";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("ApiError", () => {
  it("carries the HTTP status and is an Error", () => {
    const err = new ApiError(503, "down");
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(503);
    expect(err.message).toBe("down");
  });
});

describe("api client", () => {
  it("getSources returns the parsed list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(200, [{ name: "crtsh" }])),
    );
    expect(await getSources()).toEqual([{ name: "crtsh" }]);
  });

  it("runScan raises ApiError with the status on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(401, { detail: "bad key" })),
    );
    await expect(runScan("example.com", false, "")).rejects.toMatchObject({
      status: 401,
      message: "bad key",
    });
  });

  it("getHistory sends the API key header", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(200, []));
    vi.stubGlobal("fetch", fetchMock);
    await getHistory("SECRET");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/history",
      expect.objectContaining({ headers: { "X-API-Key": "SECRET" } }),
    );
  });

  it("fetchReport returns a blob", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, { ok: true })));
    expect(await fetchReport(1, "k")).toBeInstanceOf(Blob);
  });

  it("fetchReport raises ApiError on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(404, {})));
    await expect(fetchReport(9, "k")).rejects.toBeInstanceOf(ApiError);
  });
});
