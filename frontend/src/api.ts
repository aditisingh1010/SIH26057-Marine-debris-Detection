import type { BatchResult, ModelQuality, RunResult, RunSummary, SystemInfo } from "./types";

const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export async function health() {
  const r = await fetch(`${API}/health`);
  if (!r.ok) throw new Error("API unavailable");
  return r.json();
}

export async function getInfo(): Promise<SystemInfo> {
  const r = await fetch(`${API}/api/v1/info`);
  if (!r.ok) throw new Error("Info unavailable");
  return r.json();
}

export async function getQuality(): Promise<ModelQuality> {
  const r = await fetch(`${API}/api/v1/quality`);
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
  const r = await fetch(`${API}/api/v1/detect?${params.toString()}`, {
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

export function reportUrl(id: string, fmt: "json" | "csv") {
  return `${API}/api/v1/runs/${id}/report.${fmt}`;
}

export async function getRun(id: string): Promise<RunResult> {
  const r = await fetch(`${API}/api/v1/runs/${id}`);
  if (!r.ok) throw new Error("Run not found");
  return r.json();
}

export async function getRuns(): Promise<RunSummary[]> {
  const r = await fetch(`${API}/api/v1/runs`);
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
  const r = await fetch(`${API}/api/v1/detect/batch?${params.toString()}`, {
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
