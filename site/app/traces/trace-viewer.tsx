'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

type Trace = Record<string, any>;

const formatTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value));
const formatCost = (value: number) => value ? `$${Number(value).toFixed(6)}` : '$0';

export default function TraceViewer() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [trace, setTrace] = useState<Trace | null>(null);

  const load = useCallback(async () => {
    const payload = await (await fetch('/api/traces', { cache: 'no-store' })).json();
    const next = payload.traces || [];
    setTraces((current) => JSON.stringify(current) === JSON.stringify(next) ? current : next);
    const hash = location.hash.slice(1);
    setSelectedId((current) => current || (hash && next.some((item: Trace) => item.id === hash) ? hash : next[0]?.id || ''));
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(() => { if (!document.hidden) load(); }, 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (!selectedId) return;
    history.replaceState(null, '', `/traces#${selectedId}`);
    fetch(`/api/traces/${selectedId}`, { cache: 'no-store' }).then((response) => response.json()).then((next) => {
      setTrace((current) => JSON.stringify(current) === JSON.stringify(next) ? current : next);
    });
  }, [selectedId, traces]);

  const select = (id: string) => { setSelectedId(id); setTrace(null); };

  return (
    <>
      <section className="trace-heading">
        <div><h1>运行行迹</h1><p>从一次念头，到一首通过校验的诗。这里保留每一笔修改。</p></div>
        <button className="refresh-button" type="button" onClick={load}>刷新记录</button>
      </section>
      <section className="metric-ruler" aria-label="当前运行指标">
        <div><span>总耗时</span><strong>{trace ? `${Number(trace.duration_ms).toFixed(0)} ms` : '—'}</strong></div>
        <div><span>输入 Token</span><strong>{trace?.prompt_tokens ?? '—'}</strong></div>
        <div><span>输出 Token</span><strong>{trace?.completion_tokens ?? '—'}</strong></div>
        <div><span>估算成本</span><strong>{trace ? formatCost(trace.cost) : '—'}</strong></div>
      </section>
      <section className="trace-workspace">
        <aside className="run-index" aria-label="生成记录">
          <div className="run-index-title"><h2>近百次生成</h2><span>{traces.length}</span></div>
          <div className="run-list">
            {traces.length ? traces.map((item) => (
              <button key={item.id} type="button" className={`run-entry ${item.id === selectedId ? 'selected' : ''}`} onClick={() => select(item.id)}>
                <strong>{item.topic || '未名之思'}</strong><small><span>{formatTime(item.started_at)}</span><span>{Number(item.duration_ms).toFixed(0)} ms</span></small>
              </button>
            )) : <p className="empty-copy">生成一首诗后，行迹会留在这里。</p>}
          </div>
        </aside>
        <article className="trace-scroll">
          {!trace ? <div className="trace-empty"><div className="empty-seal">迹</div><h2>尚无行迹</h2><p>前往试诗页生成一首诗，再回来查看模型请求、工具校验和耗时。</p><Link href="/">前往试诗</Link></div> : <TraceDetail trace={trace} />}
        </article>
      </section>
    </>
  );
}

function TraceDetail({ trace }: { trace: Trace }) {
  const sourceNames: Record<string, string> = { model: '模型通过', fallback: '本地兜底', pending: '运行中' };
  const total = Math.max(1, Number(trace.prompt_tokens) + Number(trace.completion_tokens));
  return <>
    <div className="trace-title-row"><div><h2>{trace.topic || '未名之思'}</h2><p>{trace.model} · {formatTime(trace.started_at)} · {trace.event_count} 个事件</p></div><span className="source-stamp">{sourceNames[trace.source] || trace.source}</span></div>
    {trace.result && <div className="trace-poem"><strong>{trace.result.title}</strong>{trace.result.lines.map((line: string) => <span key={line}>{line}</span>)}</div>}
    <div className="token-track"><span className="prompt-part" style={{ width: `${Number(trace.prompt_tokens) / total * 100}%` }} /><span className="completion-part" style={{ width: `${Number(trace.completion_tokens) / total * 100}%` }} /></div>
    <div className="token-legend"><span>输入 {trace.prompt_tokens}</span><span>输出 {trace.completion_tokens}</span></div>
    <div className="event-stream">{trace.events.map((event: Trace, index: number) => <section className="trace-event" data-kind={event.kind} key={`${event.kind}-${index}`}><div className="event-head"><h3>{event.title}</h3><time>+{Number(event.at_ms).toFixed(1)} ms</time></div>{event.detail && Object.keys(event.detail).length > 0 && <details><summary>查看数据</summary><pre>{JSON.stringify(event.detail, null, 2)}</pre></details>}</section>)}</div>
  </>;
}
