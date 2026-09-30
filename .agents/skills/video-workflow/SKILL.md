---
name: video-workflow
description: 用户要制作、修改或导出视频时，启动本地视频工作台，依次推进需求、调研、文案、静态预览、视频制作、导出；处理批注与下游失效。
---
# 视频工作流

## 环境与启动
从仓库根目录操作。Python 3.10+ 即可启动 UI：`python -m app.server --open`。服务只监听本机。查看 `python scripts/setup.py` 的依赖检查；渲染还需要 Node.js、FFmpeg、浏览器和锁定的 npm 依赖。安装获准后运行 `python scripts/setup.py --install`。各系统浏览器可用 BROWSER_PATH 指定，不要求用户提供模型 API。

当前默认项目 `workspace/`，样例 `examples/processed-meat/`。UI 项目选择器独立查看二者，不覆盖新项目。自定义项目用 `python -m app.server --workspace path/to/project --open`。每次操作 CLI 必须使用同一个 `--workspace`。

## 文件与审核
`python -m app.cli --workspace workspace status` 返回状态、每阶段版本、批注、产物与操作历史。状态存在 `.studio/workflow.json`，不要直接覆盖；所有写入使用 CLI 或 UI。

- `save --stage requirements --file requirements.md`：读取文本保存；实际变动会建立新版本并使后续依赖失效
- `artifact --stage preview --path output/scene-01.png --label '建立问题' --role '开场问题'`：注册 workspace 内实际文件
- `submit --stage preview`：进入审核；前置阶段必须已确认
- `approve --stage preview --by agent --note '检查过截图，文字清楚且无裁切'`：仅显式自审模式可用
- `revise --stage narration`：开始新版本；重新生成或核对并注册该版本的产物
- `undo`：恢复前一状态快照；实际文件不删除
- `mode --self-review on`：仅用户明确授权这个项目自动自审时开启；新项目默认关闭

正常模式请用户在工作台点击“确认并继续”。不能用 `--by human` 假装用户点击；若用户在对话中已明确批准本阶段，可代表其记录批准，并在 note 写明对话批准内容。前一阶段回改后，每个下游都要重新处理，不能机械批准旧内容。

## 六个阶段
1. requirements：目标、受众、时长/画幅、平台、参考、事实与语气边界。缺少影响方向的内容再问。
2. research：优先原始来源。保存每项关键说法的来源、日期、支持的结论、限制和待核实问题。来源必须实际阅读。使用 sources.json 记录来源；`python -m app.sources workspace/sources.json` 检查结构，不替代事实核对。
3. narration：读取 video-narration skill，写完整讲述文本，先确认文稿。无声模式把画面/字幕文本与阅读时长写入引擎 narration.json；配音模式按对应 Edge/Azure 接入说明合成已批准文本，使用真实音频和词边界生成字幕及时间轴。短幕要有足够阅读时间，避免只为快而难读。
4. preview：自由编写 HTML 场景，真实渲染截图；按视觉角色选择，例如开场、关系解释、数字比较、关键限制、结尾。不能按固定三等分，也不能把文字卡或设计示意图称为真实截图。注册 PNG/JPEG，并写明选择理由。
5. production：静态确认后才制作完整动画/视频。读取 `.studio/workflow.json` 中 annotations；针对对应截图、时间段、版本和归一化框选坐标修改代码。不依赖固定元素 ID。记录如何处理意见，不覆盖批注。按已选模式制作无声或 Edge/Azure 配音视频，并烧录字幕。
6. export：检查实际视频时长、画幅、fps、字幕清晰度、节奏、动画边界、文件是否能播放。注册 MP4、字幕与必要源文件；未实测项目明确说明。

## 渲染接口
原项目 `vendor/html-explainer/` 保留来源和许可证。先读取相关原始文档再使用其场景 API。仓库自有 `scripts/silent_timeline.py` 从 `narration.json` 的 `id/text/duration/captions?` 写出时间轴、字幕、beats，并标注无声模式。

`python scripts/silent_timeline.py workspace`

`node vendor/html-explainer/scripts/render_video.mjs workspace --jpeg --jpeg-quality 95 --crf 18 --preset medium --concurrency 2`

`node vendor/html-explainer/scripts/check_layout.mjs workspace`

优先遵循 `scripts/engine.py --help`（若存在）的集成命令；遇到报错保留日志，给出具体失败步骤与可恢复操作。不要假报生成完成。

## 原创和系列包
系列包可作为配色、字体、图形语言、动效节奏的参考，用户可以选择，也可以完全原创。不要把具体场景布局写成所有项目必须遵守的模板。任何视觉调整仍应服从内容、证据和可读性。

## 修订与恢复
注册产物会复制至 `_artifacts/` 内容哈希路径，源文件后来变化不会改变历史预览。CLI 和 UI 使用跨进程锁。每次修改 HTML、字幕脚本或引擎配置前，通过 Git 或项目内版本备份保留实际源码；工作流 `undo` 仅恢复状态，不会回写已被手工修改的源码。UI 自动检查 Codex 产生的新状态，未保存输入不会被自动覆盖。

需求确认后、编写场景之前运行 `python scripts/engine.py configure workspace`。它把工作台 settings 中的 width/height/fps 同步到引擎 project.json，保留场景顺序与 slug，同步无声或 Edge/Azure 配音设置并准备 GSAP/frames。目标时长和视觉方向由你作为创作约束落实，不是自动转成固定模板。
