const runList = document.querySelector('#run-list');
const runCount = document.querySelector('#run-count');
const detail = document.querySelector('#trace-detail');
const refreshButton = document.querySelector('#refresh-traces');
const metrics = {
  duration: document.querySelector('#metric-duration'),
  prompt: document.querySelector('#metric-prompt'),
  completion: document.querySelector('#metric-completion'),
  cost: document.querySelector('#metric-cost'),
};

let selectedId = location.hash.slice(1) || null;
let listSignature = '';
let detailSignature = '';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatTime(value) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).format(new Date(value));
}

function formatCost(value) {
  if (!value) return '$0';
  return `$${Number(value).toFixed(6)}`;
}

function updateMetrics(trace) {
  metrics.duration.textContent = `${Number(trace.duration_ms || 0).toFixed(0)} ms`;
  metrics.prompt.textContent = String(trace.prompt_tokens || 0);
  metrics.completion.textContent = String(trace.completion_tokens || 0);
  metrics.cost.textContent = formatCost(trace.cost);
}

function renderTrace(trace) {
  updateMetrics(trace);
  detail.replaceChildren();

  const heading = el('div', 'trace-title-row');
  const headingCopy = el('div');
  headingCopy.append(
    el('h2', '', trace.topic || '未名之思'),
    el('p', '', `${trace.model} · ${formatTime(trace.started_at)} · ${trace.event_count} 个事件`),
  );
  const sourceNames = { model: '模型通过', repair: '修复通过', fallback: '本地兜底', emergency: '紧急兜底', pending: '运行中' };
  heading.append(headingCopy, el('span', 'source-stamp', sourceNames[trace.source] || trace.source));
  detail.append(heading);

  if (trace.result) {
    const poem = el('div', 'trace-poem');
    poem.append(el('strong', '', trace.result.title), ...trace.result.lines.map((line) => el('span', '', line)));
    detail.append(poem);
  }

  const total = Math.max(1, trace.prompt_tokens + trace.completion_tokens);
  const track = el('div', 'token-track');
  const promptPart = el('span', 'prompt-part');
  promptPart.style.width = `${(trace.prompt_tokens / total) * 100}%`;
  const completionPart = el('span', 'completion-part');
  completionPart.style.width = `${(trace.completion_tokens / total) * 100}%`;
  track.append(promptPart, completionPart);
  const legend = el('div', 'token-legend');
  legend.append(el('span', '', `输入 ${trace.prompt_tokens}`), el('span', '', `输出 ${trace.completion_tokens}`));
  detail.append(track, legend);

  const stream = el('div', 'event-stream');
  trace.events.forEach((event) => {
    const item = el('section', 'trace-event');
    item.dataset.kind = event.kind;
    const head = el('div', 'event-head');
    head.append(el('h3', '', event.title), el('time', '', `+${Number(event.at_ms).toFixed(1)} ms`));
    item.append(head);
    if (event.detail && Object.keys(event.detail).length) {
      const disclosure = document.createElement('details');
      disclosure.append(el('summary', '', '查看数据'));
      const pre = el('pre', '', JSON.stringify(event.detail, null, 2));
      disclosure.append(pre);
      item.append(disclosure);
    }
    stream.append(item);
  });
  detail.append(stream);
}

async function selectTrace(traceId) {
  selectedId = traceId;
  history.replaceState(null, '', `/traces#${traceId}`);
  document.querySelectorAll('.run-entry').forEach((entry) => {
    entry.classList.toggle('selected', entry.dataset.id === traceId);
  });
  const response = await fetch(`/api/traces/${traceId}`);
  if (!response.ok) return;
  const trace = await response.json();
  const nextSignature = JSON.stringify(trace);
  if (nextSignature === detailSignature) return;
  detailSignature = nextSignature;
  renderTrace(trace);
}

async function loadTraces(selectNewest = false, background = false) {
  if (!background) refreshButton.disabled = true;
  try {
    const response = await fetch('/api/traces');
    const payload = await response.json();
    const traces = payload.traces || [];
    runCount.textContent = String(traces.length);
    const nextListSignature = JSON.stringify(traces);
    if (!traces.length) {
      if (nextListSignature !== listSignature) {
        runList.replaceChildren(
          el('p', 'empty-copy', '生成一首诗后，行迹会留在这里。'),
        );
        listSignature = nextListSignature;
      }
      return;
    }
    if (nextListSignature !== listSignature) {
      runList.replaceChildren();
      traces.forEach((trace) => {
        const button = el('button', 'run-entry');
        button.type = 'button';
        button.dataset.id = trace.id;
        button.append(
          el('strong', '', trace.topic || '未名之思'),
          (() => {
            const meta = el('small');
            meta.append(el('span', '', formatTime(trace.started_at)), el('span', '', `${trace.duration_ms.toFixed(0)} ms`));
            return meta;
          })(),
        );
        button.addEventListener('click', () => selectTrace(trace.id));
        runList.append(button);
      });
      listSignature = nextListSignature;
    }
    const target = (selectedId && traces.some((trace) => trace.id === selectedId))
      ? selectedId
      : (selectNewest || !selectedId ? traces[0].id : null);
    if (target) await selectTrace(target);
  } finally {
    if (!background) refreshButton.disabled = false;
  }
}

refreshButton.addEventListener('click', () => loadTraces(true));
loadTraces(true);
setInterval(() => {
  if (!document.hidden) loadTraces(false, true);
}, 5000);
