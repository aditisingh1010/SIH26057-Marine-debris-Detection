import type { RunResult, RunSummary, SystemInfo } from "./types";

export const API = "http://127.0.0.1:8000";

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

export async function detect(
  file: File,
  metadata?: File | null,
  confThreshold?: number,
): Promise<RunResult> {
  const form = new FormData();
  form.append("file", file);
  if (metadata) form.append("metadata", metadata);
  const conf = confThreshold ?? 0.15;
  const r = await fetch(`${API}/api/v1/detect?conf_threshold=${conf}`, {
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
