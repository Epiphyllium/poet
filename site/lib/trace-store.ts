import { env } from 'cloudflare:workers';
import type { TraceRun } from './poet/types';

let initialized = false;

async function ensureSchema() {
  if (initialized) return;
  await env.DB.batch([
    env.DB.prepare(`CREATE TABLE IF NOT EXISTS traces (
      id TEXT PRIMARY KEY, topic TEXT NOT NULL, model TEXT NOT NULL, started_at TEXT NOT NULL,
      status TEXT NOT NULL, source TEXT NOT NULL, duration_ms REAL NOT NULL,
      prompt_tokens INTEGER NOT NULL, completion_tokens INTEGER NOT NULL, total_tokens INTEGER NOT NULL,
      cost REAL NOT NULL, result_json TEXT NOT NULL, events_json TEXT NOT NULL
    )`),
    env.DB.prepare('CREATE INDEX IF NOT EXISTS idx_traces_started_at ON traces(started_at DESC)'),
  ]);
  initialized = true;
}

export async function saveTrace(trace: TraceRun) {
  await ensureSchema();
  await env.DB.prepare(`INSERT INTO traces
    (id, topic, model, started_at, status, source, duration_ms, prompt_tokens, completion_tokens, total_tokens, cost, result_json, events_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
    .bind(trace.id, trace.topic, trace.model, trace.started_at, trace.status, trace.source, trace.duration_ms,
      trace.prompt_tokens, trace.completion_tokens, trace.total_tokens, trace.cost,
      JSON.stringify(trace.result), JSON.stringify(trace.events)).run();
}

function hydrate(row: Record<string, unknown>) {
  return { id: row.id, topic: row.topic, model: row.model, started_at: row.started_at, status: row.status,
    source: row.source, duration_ms: row.duration_ms, prompt_tokens: row.prompt_tokens,
    completion_tokens: row.completion_tokens, total_tokens: row.total_tokens, cost: row.cost,
    result: JSON.parse(String(row.result_json)), events: JSON.parse(String(row.events_json)) };
}

export async function listTraces() {
  await ensureSchema();
  const result = await env.DB.prepare('SELECT * FROM traces ORDER BY started_at DESC LIMIT 100').all();
  return result.results.map((row) => { const trace = hydrate(row as Record<string, unknown>); return { ...trace, title: trace.result.title, event_count: trace.events.length }; });
}

export async function getTrace(id: string) {
  await ensureSchema();
  const row = await env.DB.prepare('SELECT * FROM traces WHERE id = ? LIMIT 1').bind(id).first();
  if (!row) return null;
  const trace = hydrate(row as Record<string, unknown>);
  return { ...trace, event_count: trace.events.length };
}
