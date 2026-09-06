import { listTraces } from '@/lib/trace-store';

export async function GET() {
  return Response.json({ traces: await listTraces() });
}
