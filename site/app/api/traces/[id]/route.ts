import { getTrace } from '@/lib/trace-store';

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const trace = await getTrace(id);
    return trace ? Response.json(trace) : Response.json({ error: 'Trace 不存在' }, { status: 404 });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : '行迹读取失败' }, { status: 500 });
  }
}
