import type { Poem } from './types';

const poems: Record<string, Poem> = {
  cat: { title: '灵猫探案', lines: ['玄猫夜叩门', '轻爪踏霜痕', '鼠迹迷深巷', '功成隐月门'] },
  moon: { title: '月下清辉', lines: ['清辉照晚窗', '疏影覆寒霜', '客梦随云远', '天涯共月光'] },
  food: { title: '人间至味', lines: ['炊烟送晚香', '玉盏映檀香', '笑语盈堂暖', '人间饭菜香'] },
  space: { title: '星海归舟', lines: ['孤舟越太空', '星火照归鸿', '故土云天近', '长歌入晓钟'] },
  default: { title: '山中晚思', lines: ['山雨洗浮尘', '幽径少行人', '松风鸣石涧', '白云伴此身'] },
};

export function fallbackPoem(topic: string): Poem {
  const lower = topic.toLowerCase();
  if (/猫|侦探|案件/.test(topic)) return poems.cat;
  if (/火星|宇宙|太空|mars/.test(lower)) return poems.space;
  if (/月|夜|星/.test(topic)) return poems.moon;
  if (/饭|吃|食|美味/.test(topic)) return poems.food;
  return poems.default;
}
