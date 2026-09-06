import { pinyin } from 'pinyin-pro';

export const ENDING_CHARS: Record<string, string[]> = {
  an: ['山', '寒', '安', '残', '难', '栏'], ang: ['堂', '苍', '茫', '藏', '航', '商', '章'],
  iang: ['江', '香', '乡', '阳', '凉', '墙', '央'], uang: ['光', '霜', '窗', '床', '黄', '荒', '望'],
  en: ['门', '痕', '尘', '人', '深', '身', '根'], eng: ['灯', '城', '声', '生', '冷', '梦', '风'],
  ing: ['明', '清', '星', '庭', '影', '冰', '醒'], ong: ['空', '钟', '松', '鸿', '中', '东', '红'],
  ou: ['楼', '愁', '洲', '头', '舟', '侯'], iu: ['秋', '流', '幽', '游'], ui: ['归', '晖', '微', '辉', '飞'],
};

export function finalOf(char: string): string | null {
  if ([...char].length !== 1) return null;
  const value = pinyin(char, { pattern: 'final', toneType: 'none', type: 'array' })[0];
  return typeof value === 'string' && /^[a-züv]+$/i.test(value)
    ? value.toLowerCase().replaceAll('ü', 'v') : null;
}

export const rhymeGuide = () => Object.entries(ENDING_CHARS).map(([final, chars]) => `${final}:${chars.join('')}`).join('；');
