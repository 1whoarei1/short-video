# 科学空间 · 轨道图谱

深蓝坐标空间、琥珀天体与示意轨道；用扫描、路径绘制和量纲标签说明关系。

## 直接运行

打开 `preview.html`（可离线 file://），或从仓库 HTTP 服务打开。原生 1280×720，8 秒无声动画。
冻结代表帧：`preview.html?t=3.5&controls=0`。控制台：`render(3.5)`；任意顺序 seek 可复现。
本页是素材与动效示范，不是必须沿用的镜头模板、脚本或八秒时长要求。

## 可拆出来用的材料

- `assets/orbit-atlas.svg`：原创、可编辑 SVG
- `assets/spectrum.svg`：原创、可编辑 SVG

- `assets/poster.svg`：便携矢量封面，不依赖其他文件
- `styles.css`：材质、排版和构图；`motion.js`：以秒为输入的动效函数
- `../shared/`：纹理、缓动、播放器，可共用或拆散

## 自由改编

Use spatial paths and restrained coordinate labels to explain relationships. The supplied planet, paths and spectrum are illustrative, not data. Replace the curve with a sourced dataset before making scientific claims.

- **轨迹讲解**：Isolate one orbit path, keep the planet dim, and introduce labels at narrative beats. Put actual units and source beside real data.
- **信号对照**：Promote spectrum.svg to the main visual for an abstract signal lesson. For quantitative content replace its points and add labeled axes and uncertainty.

### 动效参考

0–1.8s: atlas arrives; 1–4s: trajectory draws; 3–5s: schematic curve appears. A marker follows a deterministic SVG path and phase text progresses.

### 竖屏改编

Stack heading, atlas and legend; remove the small curve panel or give it a dedicated scene. Keep the explicit schematic/data disclaimer visible.

### 内容边界

No physical simulation is claimed. Never present the fictional spectrum as measurements or convert decorative labels into unsupported quantities.

现有主题关联：frame-data-rollup, frame-decision-tree, frame-electric-studio。只是发现素材的标签，不强制替换主题。
文案、角色、配音、语速均由用户需求决定；这些材料没有预设人设或旁白。

## 来源与授权

全部本地文件为本次原创，按 `../LICENSE` 的 MIT 条款可商用、修改、混搭、再分发，保留许可声明。
四个外部设计网站仅列为发现/参考入口，没有复制它们的截图、模板、付费组件、商标或源码。
完整逐项来源、路径、变体、使用边界见 `manifest.json`。
