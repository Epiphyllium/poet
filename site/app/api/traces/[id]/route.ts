import { getTrace } from '@/lib/trace-store';

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const trace = await getTrace(id);
  return trace ? Response.json(trace) : Response.json({ error: 'Trace 不存在' }, { status: 404 });
}
