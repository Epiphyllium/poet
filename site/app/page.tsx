'use client';

import { FormEvent, useRef, useState } from 'react';

type Poem = { title: string; lines: string[] };

export default function Home() {
  const [topic, setTopic] = useState('');
  const [poem, setPoem] = useState<Poem | null>(null);
  const [source, setSource] = useState('');
  const [traceId, setTraceId] = useState('');
  const [status, setStatus] = useState('静候题意');
  const [message, setMessage] = useState('第一、二、四句同韵，第三句转韵。');
  const [working, setWorking] = useState(false);
  const resultRef = useRef<HTMLElement>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = topic.trim();
    if (!value) return;
    setPoem(null);
    setWorking(true);
    setStatus('正在推敲韵脚');
    setMessage('模型正在提交诗稿，校验工具会逐轮检查。');
    try {
      const response = await fetch('/api/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: value }),
      });
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        throw new Error(response.ok ? '服务返回了无法识别的内容' : '生成服务暂时不可用，请稍后重试');
      }
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '生成请求失败');
      setPoem(payload.poem);
      setSource(payload.source);
      setTraceId(payload.trace_id || '');
      setStatus('诗成');
      setMessage('格式、字数与韵脚均已通过确定性校验。');
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (error) {
      setStatus('未能成诗');
      setMessage(error instanceof Error ? error.message : '请求失败，请稍后重试。');
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="paper-shell">
      <Header active="write" />
      <section className="ink-hero" aria-labelledby="page-title">
        <img src="/mountain.svg" alt="淡墨山石与枯枝" />
        <div className="hero-copy">
          <h1 id="page-title">以一念<br />成四句</h1>
        </div>
        <div className={`hero-status ${working ? 'working' : ''}`} aria-live="polite">
          <span className="seal-dot" /><span>{status}</span>
        </div>
      </section>

      <section className="workbench" aria-label="诗歌生成工作台">
        <form className="topic-panel" onSubmit={submit}>
          <label htmlFor="topic">写下此刻想见的景象</label>
          <textarea id="topic" rows={5} maxLength={200} value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="例如：猫猫侦探、火星归航、雨夜最后一班地铁" required />
          <div className="topic-suggestions" aria-label="主题示例">
            {['月色', '猫猫侦探', 'AI时代的孤独'].map((value) => (
              <button key={value} type="button" onClick={() => setTopic(value)}>{value}</button>
            ))}
          </div>
          <div className="form-foot">
            <p>{message}</p>
            <button className="write-button" type="submit" disabled={working}>
              <span>{working ? '正在作诗' : '开始写诗'}</span>
              <span className="button-seal" aria-hidden="true">作</span>
            </button>
          </div>
        </form>

        {poem && (
          <article className="poem-sheet" ref={resultRef} aria-live="polite">
            <div className="poem-meta">
              <span>{source === 'model' ? '模型诗作 · 工具校验通过' : '本地诗库 · 确定性兜底'}</span>
              {traceId && <a href={`/traces#${traceId}`}>查看本次行迹</a>}
            </div>
            <div className="poem-stage">
              <h2>{poem.title}</h2>
              <div className="poem-lines">
                {poem.lines.map((line, index) => (
                  <p key={`${line}-${index}`}>{line.slice(0, -1)}<span className={index === 2 ? 'turn-char' : 'rhyme-char'}>{line.slice(-1)}</span></p>
                ))}
              </div>
            </div>
            <div className="rhyme-note">第一、二、四句同韵 · 第三句转韵</div>
          </article>
        )}
      </section>
    </main>
  );
}

export function Header({ active }: { active: 'write' | 'traces' }) {
  return (
    <header className="site-header">
      <a className="brand" href="/" aria-label="五言试验台首页">
        <span className="brand-mark" aria-hidden="true">詩</span>
        <span className="brand-name">五言试验台</span>
      </a>
      <nav className="site-nav" aria-label="主导航">
        <a className={active === 'write' ? 'active' : ''} href="/">试诗</a>
        <a className={active === 'traces' ? 'active' : ''} href="/traces">运行行迹</a>
      </nav>
    </header>
  );
}
