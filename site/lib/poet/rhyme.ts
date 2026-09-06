export const ENDING_CHARS: Record<string, string[]> = {
  an: ['山', '寒', '安', '残', '难', '栏'], ang: ['堂', '苍', '茫', '藏', '航', '商', '章'],
  iang: ['江', '香', '乡', '阳', '凉', '墙', '央', '巷'], uang: ['光', '霜', '窗', '床', '黄', '荒', '望'],
  ian: ['涧'], uan: ['远', '暖'], in: ['近'],
  en: ['门', '痕', '尘', '人', '深', '身', '根'], eng: ['灯', '城', '声', '生', '冷', '梦', '风'],
  ing: ['明', '清', '星', '庭', '影', '冰', '醒'], ong: ['空', '钟', '松', '鸿', '中', '东', '红'],
  ou: ['楼', '愁', '洲', '头', '舟', '侯'], iou: ['秋', '流', '幽', '游'], uei: ['归', '晖', '微', '辉', '飞'],
};

const FINAL_BY_CHAR = new Map(
  Object.entries(ENDING_CHARS).flatMap(([final, chars]) => chars.map((char) => [char, final] as const)),
);

export function finalOf(char: string): string | null {
  if ([...char].length !== 1) return null;
  return FINAL_BY_CHAR.get(char) || null;
}

export const rhymeGuide = () => Object.entries(ENDING_CHARS).map(([final, chars]) => `${final}:${chars.join('')}`).join('；');
