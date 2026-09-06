export type Poem = { title: string; lines: string[] };
export type ValidationError = { code: string; message: string; line_index: number | null };
export type ValidationResult = { ok: boolean; errors: ValidationError[]; finals: (string | null)[] };
export type TraceEvent = { at_ms: number; kind: string; title: string; detail: Record<string, unknown> };
export type TraceRun = {
  id: string; topic: string; model: string; started_at: string; status: string; source: string;
  duration_ms: number; prompt_tokens: number; completion_tokens: number; total_tokens: number;
  cost: number; result: Poem; events: TraceEvent[];
};
