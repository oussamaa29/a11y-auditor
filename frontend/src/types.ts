export type Impact = "critical" | "serious" | "moderate" | "minor";

export interface ScanSummary {
  id: number;
  url: string;
  score: number;
  critical_count: number;
  serious_count: number;
  moderate_count: number;
  minor_count: number;
  passes_count: number;
  error?: string | null;
  created_at: string;
}

export interface ViolationNode {
  html: string;
  target: string[];
  failure_summary?: string | null;
}

export interface Violation {
  id: string;
  impact: Impact;
  description: string;
  help: string;
  help_url: string;
  tags: string[];
  nodes: ViolationNode[];
}

export interface ScanDetail extends ScanSummary {
  violations: Violation[];
}
