import { env } from 'cloudflare:workers';
import { generatePoem } from '@/lib/poet/generator';
import { saveTrace } from '@/lib/trace-store';

export async function POST(request: Request) {
  try {
    const body = await request.json() as { topic?: unknown };
    if (typeof body.topic !== 'string') return Response.json({ error: 'topic 必须是字符串' }, { status: 400 });
    const original = body.topic;
    const topic = original.replace(/\s+/g, ' ').trim().slice(0, 200);
    const model = env.POET_MODEL || 'openrouter/free';
    const trace = await generatePoem(topic, env.OPENROUTER_API_KEY, model);
    try { await saveTrace(trace); } catch (error) { console.error('trace persistence failed', error); }
    return Response.json({ poem: { topic: original, ...trace.result }, source: trace.source, trace_id: trace.id });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : '生成失败' }, { status: 500 });
  }
}
