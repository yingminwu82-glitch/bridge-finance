import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "湾区融桥 GBA Bridge Finance",
  description: "跨境贸易金融智能分析与产品推荐系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
