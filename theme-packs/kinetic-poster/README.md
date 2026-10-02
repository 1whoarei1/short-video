# 动感字海报 · 主张发声

酸橙色大字、硬边黑底和标志式圆环；字形本身承担节奏，信息不靠快速闪烁。

## 直接运行

打开 `preview.html`（可离线 file://），或从仓库 HTTP 服务打开。原生 1280×720，8 秒无声动画。
冻结代表帧：`preview.html?t=3.5&controls=0`。控制台：`render(3.5)`；任意顺序 seek 可复现。
本页是素材与动效示范，不是必须沿用的镜头模板、脚本或八秒时长要求。

## 可拆出来用的材料

- `assets/message-mark.svg`：原创、可编辑 SVG
- `assets/arrow-ribbon.svg`：原创、可编辑 SVG

- `assets/poster.svg`：便携矢量封面，不依赖其他文件
- `styles.css`：材质、排版和构图；`motion.js`：以秒为输入的动效函数
- `../shared/`：纹理、缓动、播放器，可共用或拆散

## 自由改编

Use a short, strong statement. Rhythm comes from translation, width and a steady ticker, not strobing. The movement should reinforce how the line is spoken.

- **双段主张**：Use one clause per scene. Cut or slide between statements when the narration naturally changes; keep the same edge alignment.
- **箭头节奏**：Replace the circular mark with arrow-ribbon.svg. Animate its position behind the headline while preserving legibility.

### 动效参考

0–1.5s: type enters on two staggered beats; 1–2.2s: emblem expands; 1.8–2.5s: supporting line arrives. Ticker moves at constant low speed.

### 竖屏改编

Use three lines with one word per line, move the mark into a corner, and shorten or remove the ticker. For Chinese typography use 0 letter spacing and test the widest line.

### 内容边界

Avoid rapid luminance flashes, unreadably fast type and long paragraphs. The preview demonstrates rhythm, not a mandatory beat or voice rate.

现有主题关联：frame-kinetic-type, frame-bold-signal, frame-creative-voltage。只是发现素材的标签，不强制替换主题。
文案、角色、配音、语速均由用户需求决定；这些材料没有预设人设或旁白。

## 来源与授权

全部本地文件为本次原创，按 `../LICENSE` 的 MIT 条款可商用、修改、混搭、再分发，保留许可声明。
四个外部设计网站仅列为发现/参考入口，没有复制它们的截图、模板、付费组件、商标或源码。
完整逐项来源、路径、变体、使用边界见 `manifest.json`。
