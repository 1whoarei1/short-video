# 精密产品 · 光切面

冷白工作室、深色产品雕塑、精确标注与分层拆解；适合产品机制和功能介绍。

## 直接运行

打开 `preview.html`（可离线 file://），或从仓库 HTTP 服务打开。原生 1280×720，8 秒无声动画。
冻结代表帧：`preview.html?t=3.5&controls=0`。控制台：`render(3.5)`；任意顺序 seek 可复现。
本页是素材与动效示范，不是必须沿用的镜头模板、脚本或八秒时长要求。

## 可拆出来用的材料

- `assets/signal-object.svg`：原创、可编辑 SVG
- `assets/exploded-rings.svg`：原创、可编辑 SVG

- `assets/poster.svg`：便携矢量封面，不依赖其他文件
- `styles.css`：材质、排版和构图；`motion.js`：以秒为输入的动效函数
- `../shared/`：纹理、缓动、播放器，可共用或拆散

## 自由改编

Use a large isolated object and two purposeful annotations. Keep a quiet silhouette and emphasize one surface treatment; replace the concept object with authorized product imagery when available.

- **结构拆解**：Use exploded-rings.svg as the hero. Separate layers by changing their y offsets; draw leader lines after each layer settles.
- **深色工作室**：Switch canvas to #15241f, text to #e8eee4 and retain the acid-green status light. Keep labels high contrast.

### 动效参考

0–1.8s: body rises and straightens; 1.6–3.0s: labels arrive; 2.3–3.1s: layer study enters. Remaining time holds the message with restrained surface motion.

### 竖屏改编

Place title in the top 28%, product in the middle 49%, labels and layer study at the bottom. Remove one annotation rather than shrinking all type.

### 内容边界

Do not reuse concept geometry as evidence of a real device, specification or measured performance. Avoid putting every feature around the object.

现有主题关联：frame-product-promo, frame-product-promo-30s, frame-build-minimal。只是发现素材的标签，不强制替换主题。
文案、角色、配音、语速均由用户需求决定；这些材料没有预设人设或旁白。

## 来源与授权

全部本地文件为本次原创，按 `../LICENSE` 的 MIT 条款可商用、修改、混搭、再分发，保留许可声明。
四个外部设计网站仅列为发现/参考入口，没有复制它们的截图、模板、付费组件、商标或源码。
完整逐项来源、路径、变体、使用边界见 `manifest.json`。
