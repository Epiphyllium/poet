import { listTraces } from '@/lib/trace-store';

export async function GET() {
  try {
    return Response.json({ traces: await listTraces() });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : '行迹读取失败' }, { status: 500 });
  }
}
