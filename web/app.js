const form = document.querySelector('#poem-form');
const topicInput = document.querySelector('#topic');
const status = document.querySelector('#hero-status');
const message = document.querySelector('#form-message');
const submitButton = form.querySelector('button[type="submit"]');
const titleNode = document.querySelector('#poem-title');
const linesNode = document.querySelector('#poem-lines');
const sourceNode = document.querySelector('#poem-source');
const traceLink = document.querySelector('#trace-link');
const rhymeNote = document.querySelector('#rhyme-note');
const poemSheet = document.querySelector('#poem-sheet');

document.querySelectorAll('[data-topic]').forEach((button) => {
  button.addEventListener('click', () => {
    topicInput.value = button.dataset.topic;
    topicInput.focus();
  });
});

function setState(text, working = false) {
  status.querySelector('span:last-child').textContent = text;
  status.classList.toggle('working', working);
  submitButton.disabled = working;
}

function renderPoem(poem) {
  titleNode.textContent = poem.title;
  linesNode.replaceChildren();
  poem.lines.forEach((line, index) => {
    const row = document.createElement('p');
    const body = document.createTextNode(line.slice(0, -1));
    const ending = document.createElement('span');
    ending.textContent = line.slice(-1);
    ending.className = index === 2 ? 'turn-char' : 'rhyme-char';
    row.append(body, ending);
    linesNode.append(row);
  });
}

async function hydrateTrace(traceId) {
  try {
    const response = await fetch(`/api/traces/${traceId}`);
    if (!response.ok) return;
    const trace = await response.json();
    const sourceLabels = {
      model: '模型诗作 · 工具校验通过',
      repair: '修复诗作 · 校验通过',
      fallback: '本地诗库 · 确定性兜底',
      emergency: '紧急兜底',
    };
    sourceNode.textContent = sourceLabels[trace.source] || trace.source;
    const toolEvents = trace.events.filter((event) => event.kind === 'tool.result');
    const feedback = toolEvents.at(-1)?.detail?.feedback;
    if (feedback?.finals) {
      rhymeNote.textContent = `韵脚 ${feedback.finals.join(' / ')} · 第三句转韵`;
    } else {
      rhymeNote.textContent = `总耗时 ${trace.duration_ms.toFixed(0)} ms · ${trace.total_tokens} Token`;
    }
  } catch (_) {
    sourceNode.textContent = '诗作已生成';
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) {
    message.textContent = '先写下一个主题。';
    topicInput.focus();
    return;
  }

  poemSheet.hidden = true;
  setState('正在推敲韵脚', true);
  message.textContent = '模型正在提交诗稿，本地工具会逐轮校验。';
  sourceNode.textContent = '正在生成';
  traceLink.hidden = true;

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || '生成请求失败');

    renderPoem(payload.poem);
    poemSheet.hidden = false;
    setState('诗成', false);
    message.textContent = '格式与韵脚均已通过本地校验。';
    if (payload.trace_id) {
      traceLink.href = `/traces#${payload.trace_id}`;
      traceLink.textContent = '查看本次行迹';
      traceLink.hidden = false;
      await hydrateTrace(payload.trace_id);
    }
    requestAnimationFrame(() => {
      poemSheet.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  } catch (error) {
    setState('未能成诗', false);
    message.textContent = error.message || '请求失败，请检查本地服务。';
    sourceNode.textContent = '生成失败';
  }
});
