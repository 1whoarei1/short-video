# 编辑拼贴 · 野外笔记

暖纸、深红衬线字、地貌剪影、胶带与裁切线；为观点和人文主题组织层次。

## 直接运行

打开 `preview.html`（可离线 file://），或从仓库 HTTP 服务打开。原生 1280×720，8 秒无声动画。
冻结代表帧：`preview.html?t=3.5&controls=0`。控制台：`render(3.5)`；任意顺序 seek 可复现。
本页是素材与动效示范，不是必须沿用的镜头模板、脚本或八秒时长要求。

## 可拆出来用的材料

- `assets/landscape-cutout.svg`：原创、可编辑 SVG
- `assets/annotation-sheet.svg`：原创、可编辑 SVG

- `assets/poster.svg`：便携矢量封面，不依赖其他文件
- `styles.css`：材质、排版和构图；`motion.js`：以秒为输入的动效函数
- `../shared/`：纹理、缓动、播放器，可共用或拆散

## 自由改编

Build an argument with a primary headline, one paper clipping and a contrasting note. Keep overlaps intentional and let annotations point to a real narrative detail.

- **观察样本**：Duplicate the landscape cutout with different crops in a three-frame contact sheet; replace the title with an observation, not a fake publication headline.
- **页边批注**：Use annotation-sheet.svg as a source of freehand marks; inline the SVG and retain only the one mark that clarifies the argument.

### 动效参考

0–1.5s: headline and clipping arrive with different angles; 1.7–2.5s: note lands; 2.6–3.7s: red circle reveals. Hold long enough to read.

### 竖屏改编

Put masthead and title first, clipping below with a smaller note overlapping its bottom edge. Preserve at least 40px between reading text and the illustration.

### 内容边界

Do not imply these original vector mountains are documentary photographs. Avoid tiny body text or unlicensed magazine/newspaper scans.

现有主题关联：frame-bold-poster, frame-nyt-graph, frame-warm-grain。只是发现素材的标签，不强制替换主题。
文案、角色、配音、语速均由用户需求决定；这些材料没有预设人设或旁白。

## 来源与授权

全部本地文件为本次原创，按 `../LICENSE` 的 MIT 条款可商用、修改、混搭、再分发，保留许可声明。
四个外部设计网站仅列为发现/参考入口，没有复制它们的截图、模板、付费组件、商标或源码。
完整逐项来源、路径、变体、使用边界见 `manifest.json`。
