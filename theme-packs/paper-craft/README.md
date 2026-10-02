# 纸艺构造 · 小小世界

奶油纸面、折叠山谷和剪纸植物；通过分层组装解释生态、流程和日常故事。

## 直接运行

打开 `preview.html`（可离线 file://），或从仓库 HTTP 服务打开。原生 1280×720，8 秒无声动画。
冻结代表帧：`preview.html?t=3.5&controls=0`。控制台：`render(3.5)`；任意顺序 seek 可复现。
本页是素材与动效示范，不是必须沿用的镜头模板、脚本或八秒时长要求。

## 可拆出来用的材料

- `assets/paper-garden.svg`：原创、可编辑 SVG
- `assets/folded-bird.svg`：原创、可编辑 SVG

- `assets/poster.svg`：便携矢量封面，不依赖其他文件
- `styles.css`：材质、排版和构图；`motion.js`：以秒为输入的动效函数
- `../shared/`：纹理、缓动、播放器，可共用或拆散

## 自由改编

Use layer assembly to explain a process: background support, core idea, then living detail. Adjust polygon shapes and mild shadows to suit your topic.

- **三步构造**：Use three separate pieces from the garden SVG for three process cards. Reveal each after its explanation rather than at equal fixed intervals.
- **平面剪纸**：Remove shadows, use two colors and replace the bird with a topic-specific simple shape for a clean educational graphic.

### 动效参考

0–1.5s: supporting paper discs stack; .8–2.2s: garden rises; 1.5–2.7s: bird folds into view; 2.7–3.4s: sticker lands.

### 竖屏改编

Set headline above the circular scene; move the three step labels into a horizontal footer and drop the sticker if the composition gets crowded.

### 内容边界

The preview is vector artwork, not photographed handmade paper. Do not rely on folds as accurate origami instructions.

现有主题关联：frame-play-mode, frame-warm-grain, frame-decision-tree。只是发现素材的标签，不强制替换主题。
文案、角色、配音、语速均由用户需求决定；这些材料没有预设人设或旁白。

## 来源与授权

全部本地文件为本次原创，按 `../LICENSE` 的 MIT 条款可商用、修改、混搭、再分发，保留许可声明。
四个外部设计网站仅列为发现/参考入口，没有复制它们的截图、模板、付费组件、商标或源码。
完整逐项来源、路径、变体、使用边界见 `manifest.json`。
