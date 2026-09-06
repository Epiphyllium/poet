import { ENDING_CHARS, rhymeGuide } from './rhyme';
import { fallbackPoem } from './fallback';
import { validatePoem } from './validator';
import type { Poem, TraceEvent, TraceRun, ValidationResult } from './types';

type Usage = { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number; cost?: number };

const SYSTEM_PROMPT = `你是一位擅长古典汉语的五言诗人。围绕主题创作一首四句五言古诗。
硬约束：标题二至八个汉字；恰好四句；每句恰好五个汉字；标题和诗句只含汉字；第一、第二、第四句末字的普通话韵母完全相同（忽略声调）；第三句必须使用不同韵母。
避免现代词汇直译，把现代主题转化为古典意象。四句要有起承转合、场景统一、表达自然。必须调用 submit_poem。`;

function chooseTarget(finals: (string | null)[], preferred?: string | null) {
  if (preferred) return preferred;
  const values = [finals[0], finals[1], finals[3]].filter((value): value is string => Boolean(value));
  const counts = new Map<string, number>();
  values.forEach((value) => counts.set(value, (counts.get(value) || 0) + 1));
  return [...counts].sort((a, b) => b[1] - a[1] || Number(Boolean(ENDING_CHARS[b[0]])) - Number(Boolean(ENDING_CHARS[a[0]])))[0]?.[0] || null;
}

function toolFeedback(poem: Poem, validation: ValidationResult, preferred?: string | null) {
  const target = chooseTarget(validation.finals, preferred);
  const suggested = target ? ENDING_CHARS[target] || [] : [];
  const incorrect = new Set<number>();
  const errors = validation.errors.filter((error) => !['rhyme_mismatch', 'third_line_rhymes'].includes(error.code));
  if (validation.finals.length === 4 && target) {
    for (const index of [0, 1, 3]) {
      if (validation.finals[index] !== target) {
        incorrect.add(index);
        errors.push({ code: 'rhyme_mismatch', line_index: index, message: `第${index + 1}句末字“${poem.lines[index].slice(-1)}”的韵母是 ${validation.finals[index]}，正确目标韵母是 ${target}` });
      }
    }
    if (validation.finals[2] === target) {
      incorrect.add(2);
      errors.push({ code: 'third_line_rhymes', line_index: 2, message: `第3句末字“${poem.lines[2].slice(-1)}”与目标韵相同，但第三句必须转韵` });
    }
  }
  errors.forEach((error) => { if (error.line_index !== null) incorrect.add(error.line_index); });
  const incorrectLines = [...incorrect].sort().map((index) => index + 1);
  const preserveLines = poem.lines.map((_, index) => index + 1).filter((line) => !incorrectLines.includes(line));
  const lineLabel = incorrectLines.map((line) => `第${line}句`).join('、');
  const preserveLabel = preserveLines.map((line) => `第${line}句`).join('、');
  const instruction = validation.ok ? '诗歌已通过全部硬约束' :
    `${errors.map((error) => error.message).join('；')}。只重写${lineLabel || '错误部分'}，${preserveLabel || '其余内容'}保持原样。${target ? `目标韵母是 ${target}` : ''}${suggested.length ? `，建议末字：${suggested.join('、')}` : ''}。修改后提交完整标题和四句诗。`;
  return {
    accepted: validation.ok, finals: validation.finals,
    required_scheme: '第1、2、4句韵母相同；第3句韵母不同',
    recommended_rhyme_final: target, recommended_end_chars: suggested,
    incorrect_lines: incorrectLines, preserve_lines: preserveLines,
    line_checks: poem.lines.map((line, index) => ({ line_number: index + 1, text: line, end_char: line.slice(-1), final: validation.finals[index], status: incorrect.has(index) ? '需修改' : '正确' })),
    errors, instruction,
  };
}

export async function generatePoem(topic: string, apiKey: string | undefined, model: string): Promise<TraceRun> {
  const started = performance.now();
  const id = crypto.randomUUID().replaceAll('-', '').slice(0, 12);
  const events: TraceEvent[] = [];
  const usage = { prompt: 0, completion: 0, total: 0, cost: 0 };
  const event = (kind: string, title: string, detail: Record<string, unknown> = {}) => events.push({ at_ms: Math.round((performance.now() - started) * 10) / 10, kind, title, detail });
  event('run.start', '开始生成', { topic, model });
  let poem: Poem | null = null;
  let source = 'fallback';

  if (apiKey) {
    const tool = { type: 'function', function: { name: 'submit_poem', description: '提交诗稿给确定性校验器；未通过时按照返回的错误行、目标韵母和推荐韵脚修改。', strict: true,
      parameters: { type: 'object', properties: { title: { type: 'string', minLength: 2, maxLength: 8 }, lines: { type: 'array', minItems: 4, maxItems: 4, items: { type: 'string', minLength: 5, maxLength: 5 } } }, required: ['title', 'lines'], additionalProperties: false } } };
    const messages: Array<Record<string, unknown>> = [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: `主题：${topic || '未名之思'}\n严格同韵字参考组：${rhymeGuide()}。第一、二、四句从同一组选择末字，第三句不得使用该组。` },
    ];
    let preferred: string | null = null;
    try {
      for (let attempt = 1; attempt <= 4; attempt += 1) {
        event('tool.attempt', `第 ${attempt} 次提交`, { attempt, max_attempts: 4 });
        event('model.request', '发送模型请求', { model });
        const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
          method: 'POST', headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json', 'X-Title': 'Five Character Poet' },
          body: JSON.stringify({
            model,
            messages,
            tools: [tool],
            tool_choice: { type: 'function', function: { name: 'submit_poem' } },
            parallel_tool_calls: false,
            temperature: 0.8,
            max_tokens: 1200,
            reasoning: { enabled: false },
          }),
        });
        if (!response.ok) throw new Error(`OpenRouter ${response.status}`);
        const result = await response.json() as { choices?: Array<{ finish_reason?: string; message?: Record<string, unknown> }>; usage?: Usage };
        const currentUsage = result.usage || {};
        usage.prompt += Number(currentUsage.prompt_tokens || 0); usage.completion += Number(currentUsage.completion_tokens || 0);
        usage.total += Number(currentUsage.total_tokens || 0); usage.cost += Number(currentUsage.cost || 0);
        event('model.response', '收到模型响应', { finish_reason: result.choices?.[0]?.finish_reason || 'unknown', usage: currentUsage });
        const message = result.choices?.[0]?.message;
        const calls = message?.tool_calls as Array<{ id?: string; function?: { arguments?: string } }> | undefined;
        if (!message || !calls?.length) throw new Error('模型未调用 submit_poem');
        messages.push(message);
        const call = calls[0];
        let candidate: Poem;
        try { candidate = JSON.parse(call.function?.arguments || '{}') as Poem; }
        catch { throw new Error('工具参数不是合法 JSON'); }
        const validation = validatePoem(candidate);
        const feedback = toolFeedback(candidate, validation, preferred);
        if (!preferred && typeof feedback.recommended_rhyme_final === 'string') preferred = feedback.recommended_rhyme_final;
        event('tool.result', '校验诗稿', { attempt, poem: candidate, feedback });
        if (validation.ok) { poem = candidate; source = 'model'; event('candidate.valid', '候选通过校验'); break; }
        messages.push({ role: 'tool', tool_call_id: call.id, name: 'submit_poem', content: JSON.stringify(feedback) });
      }
    } catch (error) {
      event('generation.error', '模型生成失败', { error: error instanceof Error ? error.message : String(error) });
    }
  } else event('generation.skip', '未配置模型密钥');

  if (!poem) { poem = fallbackPoem(topic); source = 'fallback'; event('fallback.selected', '采用本地兜底', { title: poem.title }); }
  const finalValidation = validatePoem(poem);
  if (!finalValidation.ok) {
    throw new Error(`最终诗稿未通过硬校验：${finalValidation.errors.map((error) => error.message).join('；')}`);
  }
  event('run.finish', '生成结束', { source });
  return { id, topic, model, started_at: new Date().toISOString(), status: 'completed', source,
    duration_ms: Math.round((performance.now() - started) * 10) / 10,
    prompt_tokens: usage.prompt, completion_tokens: usage.completion, total_tokens: usage.total,
    cost: usage.cost, result: poem, events };
}
