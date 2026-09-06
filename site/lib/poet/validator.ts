import { finalOf } from './rhyme';
import type { Poem, ValidationError, ValidationResult } from './types';

const HAN = /^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+$/u;

export function validatePoem(value: unknown): ValidationResult {
  const errors: ValidationError[] = [];
  if (!value || typeof value !== 'object') return { ok: false, errors: [{ code: 'invalid_shape', message: '诗稿必须是对象', line_index: null }], finals: [] };
  const poem = value as Poem;
  if (typeof poem.title !== 'string' || !Array.isArray(poem.lines) || !poem.lines.every((line) => typeof line === 'string')) {
    return { ok: false, errors: [{ code: 'invalid_shape', message: '必须包含字符串标题和诗句数组', line_index: null }], finals: [] };
  }
  const titleLength = [...poem.title].length;
  if (titleLength < 2 || titleLength > 8) errors.push({ code: 'title_length', message: '标题必须由二至八个汉字组成', line_index: null });
  if (!HAN.test(poem.title)) errors.push({ code: 'title_chars', message: '标题只能包含汉字', line_index: null });
  if (poem.lines.length !== 4) errors.push({ code: 'line_count', message: '诗句必须恰好为四句', line_index: null });
  poem.lines.forEach((line, index) => {
    if ([...line].length !== 5) errors.push({ code: 'line_length', message: `第${index + 1}句必须恰好五个汉字`, line_index: index });
    if (!HAN.test(line)) errors.push({ code: 'line_chars', message: `第${index + 1}句只能包含汉字`, line_index: index });
  });
  const finals = poem.lines.length === 4 && poem.lines.every(Boolean) ? poem.lines.map((line) => finalOf([...line].at(-1) || '')) : [];
  if (finals.length === 4) {
    if (finals.some((value) => !value)) errors.push({ code: 'rhyme_unknown', message: '无法取得韵脚', line_index: null });
    else {
      for (const index of [1, 3]) if (finals[index] !== finals[0]) errors.push({ code: 'rhyme_mismatch', message: `第${index + 1}句韵母 ${finals[index]} 与第一句 ${finals[0]} 不同`, line_index: index });
      if (finals[2] === finals[0]) errors.push({ code: 'third_line_rhymes', message: '第三句必须转韵', line_index: 2 });
    }
  }
  return { ok: errors.length === 0, errors, finals };
}
