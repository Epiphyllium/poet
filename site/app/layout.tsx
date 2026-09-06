import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '五言试验台',
  description: '一个以大模型负责创作、确定性工具负责守住格式与韵脚的五言古诗生成系统。',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
