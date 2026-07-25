import type { ScanDetail, ScanSummary } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8020";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erreur ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  runScan: (url: string) =>
    request<ScanDetail>(`/api/scans`, { method: "POST", body: JSON.stringify({ url }) }),
  listScans: () => request<ScanSummary[]>(`/api/scans`),
  getScan: (id: number) => request<ScanDetail>(`/api/scans/${id}`),
  deleteScan: (id: number) => request<void>(`/api/scans/${id}`, { method: "DELETE" }),
};
