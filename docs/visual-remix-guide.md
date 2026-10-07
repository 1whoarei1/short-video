# 用材料创作新的画面

材料库的作用，是让 AI 有更多可拿来试的东西：一张图、一种质感、一段运动、一种观察角度。先想清这句话最值得观众看见什么，再选少量材料，让它们为当前内容服务。

与 [创作与验收参考](creative-method.md) 一起使用：先问如何用图形表达关系、变化、比较和因果，镜头内部逐步推进解释，跨镜头保留或变形主体。字体、核心palette、材质与标识贯穿全片；构图及有意的明暗变化自由，不固定同一底色。原生生图与代码图形混用前检查设计语言，避免写实照片和扁平卡片未经协调就像两部片。

## 从一句话到一幕

1. 读当前需求与已批准文案，写下本幕最重要的视觉动词：靠近、拆开、连接、聚拢、穿过、浮现、展开、对比等。这个动词只是构思提示，随创作随时调整。
2. 搜索相关的两三个资源，打开短动画，再看素材清单和源码中的对应片段。一次看少量真正相关的材料，更容易形成新的组合。
3. 用真实主体、实际图片和几行画面文案做一张代表帧。文字、图表和事实数据由代码及核验来源承担；质感、物件、环境可以按需生图。
4. 先完成最难的两三秒运动，实际跳帧查看前、中、后状态，再扩展整幕。遇到复杂代码可以把工作分成素材、构图、运动与检查，但同一场景始终共用最新文件和清晰的修改范围。
5. 按内容重新决定比例、颜色、镜头、动线和节奏，保留用户选择的旁白、人物、音色与语速。样例的镜头长度只说明该示范怎么播放。

## 可借用的材料与方法

| 当前要表达的内容 | 值得先看的资源 | 可以单独借用的部分 |
|---|---|---|
| 物件的质感与细节 | precision-product / prismatic-lab / food-editorial | 物件透明图片、局部放大、扫光、倒影、剖开层次 |
| 一个系统内部怎么联系 | blueprint-mechanism / signal-journey | 通道、外壳、路径、分支汇合、聚焦镜头 |
| 资料之间的线索 | editorial-collage / tactile-archive / cinematic-inquiry | 版画、纸张、手写标记、透镜、连接路径 |
| 环境与空间感 | cinematic-landscape / scientific-space / organic-light | 远近层次、前景遮挡、光雾、轨道、材质 |
| 数据关系与变化 | editorial-data / kinetic-poster | 原创柱体、网格、字形、强调节奏；真实数字另行核验 |
| 微观观察或手工感 | botanical-microscopy / paper-craft | 薄膜、切片、折纸、植物、遮罩和逐层显露 |

这些对应关系是检索入口。一个物件也可以进入山谷，一条路线也可以写在纸上，跨包组合与新画法都可以自由采用。

## 在当前项目里实际使用

从仓库根目录运行：

```sh
python -m app.theme_resources list --query "玻璃 产品"
python -m app.theme_resources show prismatic-lab
python -m app.theme_resources copy prismatic-lab --workspace PROJECT_PATH
python -m app.theme_resources copy cinematic-landscape --workspace PROJECT_PATH
```

领取工作流任务后，每次 copy 加 `--task-id ID --revision REV`，使用最新 revision 和最初固定的绝对 PROJECT_PATH。命令返回真实预览、清单和复制记录路径。共享文件只保存一份；已有修改会被保护。需要第二份可编辑试验时指定新的 `--destination assets/theme-resources-study`。

复制结果保留完整相对路径，方便从源码中拆取图片、SVG 与代码。渲染场景放在当前项目 frames/，从那里重新核对资源引用；HTML 的 base 标签是可选方法，路径都以真实文件为准。保持场景自己的时间驱动接口。采用示例播放器时可用 shared/engine-bridge.js 接上引擎；自行创作的 GSAP 或其他原生 JS 场景继续使用其适用接口。

`layout.json` 的场景键与 `project.json.order` 对应，场景时长使用数值 `duration_sec`。优先让已有时间轴命令根据已批准文稿与真实音频生成文件。手写时先检查格式，缺少有效时长会明确停止渲染。

## 生图与实际画面

当前会话有原生生图工具时，按 `.agents/skills/video-image-assets/SKILL.md` 取得真实文件、解码、登记不可变快照，再把返回路径放入场景。模型名称以工具真实报告为准。素材来源记录帮助复用，图片的真实性、使用边界与最终画面仍需检查。

Canvas 或异步创建图片时，可以把加载/解码任务放入 `window.__assetsReady` Promise。渲染器会等待它和 DOM 图片完成，超时或缺图会报错。背景图、SVG 外链及复杂异步纹理也应明确等待，并查看真正导出的代表帧。

## 成功的检查方式

- 内容：观众看完这一幕，是否更容易理解这句话
- 视觉：主体、层次和视线方向是否明确，文字能否读完
- 运动：同一秒反复或倒序取样，是否回到同一画面
- 推进：实际连续播放时，镜头内是否逐步建立关系或改变状态，而非只有静态文字入场；跨镜头能否跟住主体
- 连贯：编码后的代表帧是否保持字体、palette、材质与标识；明暗变化是否仍属于同一设计语言
- 素材：图片是否真的加载，透明边缘、裁切、比例与清晰度是否合适
- 导出：实际视频的画幅、帧数、时长、音轨和字幕是否匹配当前项目

代表画面按视觉角色选择：最难表现的关系、关键转场、主要风格或信息密集处。可选开头或结尾，只要能帮助判断整片方向。沿用当前工作流审核模式，无需为每种材料另加一次审核。

## 已有可运行实践

- [continuous-motion](../examples/continuous-motion/README.md)：同一主体连续变形，光标按真实锚点完成操作，外壳与内容分层交接；配套 [连续运动实践](continuous-motion.md) 说明共享几何、速度继承、确定性采样和成片检查。按内容拆用，不沿用固定外观或时长
- `examples/causal-motion/`：10 秒两镜头示意，把新引入的 HXM 动作组成触发、建图、原因标注与结论；同一圆点和基期柱跨镜头保留，使用已有 engine-bridge 接上真实 `__tl`。打开 `index.html` 可看短预览，README 有导出、倒序 seek 测试和实测代表帧
- `examples/strawberry-remix/`：实际生成的草莓图片，结合纸张、局部观察与路径，重组为六幕 24 秒短片
- `examples/mountain-letter/`：借用山脊、松枝、触感版画与折纸鸟，以一封信贯穿重新创作的 28 秒短片；用持续主体连接三个不同场景
- `examples/image-material-study/`：真实透明棱镜图片的保存、来源记录与 HTML 使用
- 各包 README 的 variants：同一批材料可以使用不同构图或视角；主题清单是素材索引，最终画面由当前内容决定

这些实践证明资源能组合、图片能落盘、代码能渲染。针对 GPT-6-Luna 的质量提升程度仍需在实际新会话制作中评估，不能用包数量或自动测试通过代替审美判断。

HXM 是可选数值动效工具，见 `vendor/html-explainer/references/motion-library.md`；视觉主语、因果运动与跨镜头承接见 `references/showcase-mode.md`（同一 vendor 目录）。这些建议服务当前内容，尊重用户主题与现有审核模式，不强制每幕运镜、固定布局或默认快门。只定义 `__seek` 不足以导出；使用 GSAP `onUpdate` 长度载体或现有 `engine-bridge.js` 接到 `__tl`。
