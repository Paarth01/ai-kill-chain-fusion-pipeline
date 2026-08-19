import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// api.ts reads import.meta.env.VITE_API_BASE_URL / VITE_API_KEY at module
// load time, so each test that needs a different env value must stub the
// env, reset the module registry, and re-import — otherwise every test
// would share whatever the first import captured.
describe("api client", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("sends no X-API-Key header when VITE_API_KEY is unset", async () => {
    vi.stubEnv("VITE_API_KEY", "");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ source_type: "uav_uas", degraded: true }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { toggleEW } = await import("./api");
    await toggleEW("uav_uas");

    const [url, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/ew/toggle?source_type=uav_uas");
    expect(options.headers).toEqual({});
  });

  it("sends X-API-Key header when VITE_API_KEY is set", async () => {
    vi.stubEnv("VITE_API_KEY", "secret123");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ source_type: "elint", degraded: false }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { toggleEW } = await import("./api");
    await toggleEW("elint");

    const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(options.headers).toEqual({ "X-API-Key": "secret123" });
  });

  it("prefixes requests with VITE_API_BASE_URL when set", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://backend.example.com");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({}),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { acknowledgeTrack } = await import("./api");
    await acknowledgeTrack("TRK-ABC123");

    const [url] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("https://backend.example.com/tracks/TRK-ABC123/ack");
  });

  it("uses relative paths when VITE_API_BASE_URL is unset", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({}) }));
    vi.stubGlobal("fetch", fetchMock);

    const { assessTrack } = await import("./api");
    await assessTrack("TRK-XYZ", "resolved");

    const [url] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/tracks/TRK-XYZ/assess?summary=resolved");
  });

  it("throws with the response body when the request fails", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      text: async () => "Track not found",
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { acknowledgeTrack } = await import("./api");
    await expect(acknowledgeTrack("missing-track")).rejects.toThrow("Track not found");
  });
});
