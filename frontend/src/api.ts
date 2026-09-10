import type { BatchResult, ModelQuality, RunResult, RunSummary, SystemInfo } from "./types";

const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

async function fetchApi(path: string, options?: RequestInit): Promise<Response> {
  const url = `${API}${path}`;
  try {
    const res = await fetch(url, options);
    if ((res.status === 502 || res.status === 504) && !API) {
      throw new Error(`Proxy error ${res.status}`);
    }
    return res;
  } catch (err) {
    if (!API && typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
      const fallbackUrl = `http://127.0.0.1:8000${path}`;
      return await fetch(fallbackUrl, options);
    }
    throw err;
  }
}

export async function health() {
  const r = await fetchApi("/health");
  if (!r.ok) throw new Error("API unavailable");
  return r.json();
}

export async function getInfo(): Promise<SystemInfo> {
  const r = await fetchApi("/api/v1/info");
  if (!r.ok) throw new Error("Info unavailable");
  return r.json();
}

export async function getQuality(): Promise<ModelQuality> {
  const r = await fetchApi("/api/v1/quality");
  if (!r.ok) throw new Error("Quality summary unavailable");
  return r.json();
}

export async function detect(
  file: File,
  metadata?: File | null,
  confThreshold?: number,
  mode: "demo" | "survey" | "custom" = "demo",
): Promise<RunResult> {
  const form = new FormData();
  form.append("file", file);
  if (metadata) form.append("metadata", metadata);
  const conf = confThreshold ?? 0.25;
  const params = new URLSearchParams({
    conf_threshold: String(conf),
    mode,
  });
  const r = await fetchApi(`/api/v1/detect?${params.toString()}`, {
    method: "POST",
    body: form,
  });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const body = await r.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await r.text();
    }
    throw new Error(detail);
  }
  return r.json();
}

export function imageUrl(id: string) {
  return `${API}/api/v1/runs/${id}/image`;
}

export function annotatedImageUrl(id: string) {
  return `${API}/api/v1/runs/${id}/image/annotated`;
}

export function reportUrl(id: string, fmt: "json" | "csv" | "geojson") {
  return `${API}/api/v1/runs/${id}/report.${fmt}`;
}

export async function getRun(id: string): Promise<RunResult> {
  const r = await fetchApi(`/api/v1/runs/${id}`);
  if (!r.ok) throw new Error("Run not found");
  return r.json();
}

export async function getRuns(): Promise<RunSummary[]> {
  const r = await fetchApi("/api/v1/runs");
  if (!r.ok) return [];
  return r.json();
}

export async function detectBatch(
  files: File[],
  confThreshold: number = 0.25,
  mode: "demo" | "survey" | "custom" = "demo",
): Promise<BatchResult> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const params = new URLSearchParams({
    conf_threshold: String(confThreshold),
    mode,
  });
  const r = await fetchApi(`/api/v1/detect/batch?${params.toString()}`, {
    method: "POST",
    body: form,
  });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const body = await r.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await r.text();
    }
    throw new Error(detail);
  }
  return r.json();
}

export async function updateRunMetadata(runId: string, metadata: Record<string, any>): Promise<RunResult> {
  const r = await fetchApi(`/api/v1/runs/${runId}/metadata`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metadata),
  });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const body = await r.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await r.text();
    }
    throw new Error(detail);
  }
  return r.json();
}

