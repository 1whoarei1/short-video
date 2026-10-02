# HTML-first 自由视觉材料库

十五个可拆用资源包，每包都有可运行的 8–12 秒动画、真实本地素材、CSS 视觉语言、按时间确定的 JS 动效、变体建议与逐项来源。SVG/代码图形和实际 AI 生成图片均标明来源。打开 `index.html` 查看。

这些是 **可拆用、可混搭的创作材料**。不改变内置 23 主题的 ID，不要求固定元素结构，不强制 React、Remotion、GSAP、任何组件库或固定模板。原创代码与 SVG 使用 MIT 许可；AI 图片标为 generated-original，并保留生成记录，这一标签并非独立的第三方许可或权利保证。无网络、无打包、无安装步骤。

| 包 | 视觉语言 | 可编辑原创材料 |
|---|---|---|
| precision-product | 精密产品 / 光切面 | 概念产品、分解层环、矢量封面 |
| editorial-collage | 编辑拼贴 / 野外笔记 | 地貌剪影、手绘批注、矢量封面 |
| scientific-space | 科学空间 / 轨道图谱 | 示意天体与轨道、非实测信号曲线、矢量封面 |
| paper-craft | 纸艺构造 / 小小世界 | 纸山谷与植物、折纸鸟、矢量封面 |
| kinetic-poster | 动感字海报 / 主张发声 | 几何圆环、箭头带、矢量封面 |
| organic-light | 有机光感 / 叶隙之间 | 透光叶片、等高线石块、矢量封面 |
| editorial-data | 编辑数据 / 关系的形状 | 折叠纸柱、等轴网格、中文数据雕塑构型 |
| botanical-microscopy | 植物显微 / 内部的秩序 | 想象横截面、透明薄膜、居中剖面标注 |
| tactile-archive | 触感档案 / 时间的切片 | 三张原创版画、六格接触印样、纸片透视 |
| cinematic-inquiry | 电影式观察 · 线索相遇 | 从三张材料切片进入局部观察，再让路径汇合成新的问题；宽幅接触印样与圆形透镜共同组织三幕微叙事。 |
| blueprint-mechanism | 蓝图构造 · 看懂一条路径 | 以斜向机构为舞台，让外壳剖开、内部通道显露、两路标记汇合；完整演示从表面到关系的观察过程。 |
| food-editorial | 食物特写 · 莓好一刻 | 真实生图素材与纸张、镜头聚焦和排字自由重组；通过新的草莓题材演示跨资源组合。 |
| signal-journey | 信号旅程 · 空间讲解 | 原创空间路径、分层节点、三路探索与汇合；通过镜头深度和沿线消息运动讲清抽象关系。 |
| prismatic-lab | 棱镜实验 · 光的材质 | 光学玻璃微距、光束切面与光谱焦散，带真实生成透明棱镜和可编辑矢量光学材质。 |
| cinematic-landscape | 电影地貌 · 山谷醒来 | 六层原创山脊、侧光薄雾、侵蚀纹理、松枝前景与溪流反光；用镜头穿行讲述十二秒山间光影。 |

## 快速使用

1. 在浏览器直接打开某包 `preview.html`。自动播放 8–12 秒循环，可暂停、拖动时间条；系统开启减少动态效果时默认静止在该包时长的 62% 处。
2. 用 `preview.html?t=3.5&controls=0` 查看无控制条的确定帧。控制台 `render(3.5)` / `renderAt(3.5)` 均按秒 seek，并暂停播放。输入值被限制到 0–该包时长。
3. 复制需要的 SVG/CSS/JS 到视频项目，把 `shared/` 同时复制并修正相对引用，或仅拆取所需原语。不要只复制 HTML 丢失资源。
4. 重写内容、拆分叙事镜头、按真实旁白或自然无声阅读长度编排。示范时长不约束成片时长。文案、角色、配音、语速始终由用户要求决定。
5. 主画板为 1280×720，窗口缩放会等比留边；不是自动横转竖。各包 README 提供竖屏重排建议。中文换字后取消负字距并检查换行、字号和字幕安全区。

## 接口与约定

- `catalog.json` 是小型发现索引。`manifest.schema.json` 是每包清单的 JSON Schema；`catalog.schema.json` 定义索引。
- 清单内所有文件路径都从仓库根目录开始，使用 `/`，不得是绝对路径、URL 或包含 `..`。HTML/CSS 的引用则是正常相对路径。
- `compatibleThemeIds` 只表示相近视觉方向，让代理能从已有 23 主题找到材料；不替换、不锁定选择。
- `shared/motion.js` 提供 clamp/progress/ease/smooth/mix/reveal/set。它们不依赖 DOM ID、框架、真实时间或随机数。
- 每包 `drawTheme(t)` 接收秒数，每次重算全部动画状态。`shared/player.js` 只负责播放、暂停、窗口适配、时间条与无障碍偏好。
- `shared/materials/` 有原创点状纹理、网格、套准标志、柔光，可单独使用。
- `assets/poster.svg` 是独立矢量封面，不是假装截图；真实 HTML 预览动画与封面构图可能不同。

### 可选：接入现有 renderer 的时间接口

现有 vendor renderer 按 `window.__tl.pause(t, false)`、`.time()`、`.duration()` 取帧。`shared/engine-bridge.js` 为这三个调用提供最小适配器，**不是 GSAP**，不模拟它的完整 API。

在复制后的场景 HTML 里，把以下脚本放在 `player.js` 后面：

```html
<script src="../shared/engine-bridge.js"></script>
```

适配器会拒绝覆盖已有的 `__tl`。正常自行创作的 GSAP 场景不需要它。还需要根据实际项目保留引擎的 frame/字幕/音频契约、正确资源路径并完成完整导出检查；提供此适配器不等于这些示范通过了完整生产/音轨验证。

## 素材与来源边界

本材料库的代码、SVG 和示范文案为原创，另有经过实际生成与核验的图片素材。每个资产以 manifest 与附带记录为准；生成记录和文件哈希不等于独立认证的版权或模型来源。没有打包参考网站的付费组件或源码。材料包使用系统字体；工作台另有为旧 23 个主题保存的 OFL 字体子集，其许可在 web/presets/themes/fonts/。字体度量跨系统可能不同。

以下是用户指定的发现入口，记录在每包 provenance，**没有把这些站点的许可等同于本包 MIT**：

- https://styles.refero.design/ — 设计语言与 DESIGN.md 发现入口
- https://superdesign.dev/ — 设计参考入口
- https://ui.aceternity.com/ — 动效组件参考入口
- https://reactbits.dev/ — 表现性动效参考入口

不要直接复制这些网站内容到公开仓库，除非对具体资源另行核验许可。库中产品、山谷、星球、曲线、纸艺和植物均是示意图；如果视频提出事实、数据或产品功能主张，必须换成经过授权和核验的材料。

## 验证

无需安装任何依赖的静态检查：

```sh
python theme-packs/tests/check_packs.py
```

已有 Playwright/Chromium 时，运行浏览器检查（不自动安装）：

```sh
BROWSER_PATH=/usr/bin/chromium node theme-packs/tests/verify_previews.cjs
```

默认仅把截图/报告写入系统临时目录；设 `THEME_QA_DIR` 可改输出位置。可用 `THEME_PACK_IDS=editorial-data,botanical-microscopy,tactile-archive` 仅检查指定包（未知 ID 会报错）；不设置则覆盖完整目录。截图包含桌面关键帧、390px 窄窗和减少动态效果静帧。检查全部包的本地资源、脚本错误、时间乱序 seek 重现、时间推进差异、拖动暂停、减少动态效果、窄窗口与可选引擎桥接。播放页完全离线；测试不访问参考网站。检查通过不等于所有浏览器、中文替换、竖屏重排或最终成片都验证过。

## 三幕微叙事扩展

- 电影式观察 `cinematic-inquiry`：三联材料 → 圆形透镜 → 路径汇合；可运行全域观察变体
- 蓝图构造 `blueprint-mechanism`：透视进入 → 外壳剖开 → 两路汇合；可运行平面读图变体
- 共享 `shared/narrative-motion.js`：纯时间的遮罩、透镜、焦点、贝塞尔汇合与透视姿态；全部可选，支持独立拆用

两个新包通过 manifest.assets 显式列出跨包复用的原创材料。复制包时也复制列出的跨包路径。叙事原语单元测试：`node theme-packs/tests/narrative-motion.cjs`。

## 生图材料与新题材实测

food-editorial 使用实际原生生图工具生成的草莓图像，保留提示词/哈希/透明通道记录，并组合共享纸张与 NarrativeMotion。8 秒预览之外，preview.html?full=1 可看 24 秒重组，examples/strawberry-remix 可由现有引擎导出。图像标记 generated-original，与代码/SVG 的 MIT 来源区分；未声称确切生成模型或测得 Luna 质量提升。
