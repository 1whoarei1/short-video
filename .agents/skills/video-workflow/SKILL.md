---
name: video-workflow
description: 用户要制作、修改或导出视频时，启动本地视频工作台，按人工/半自动/全自动模式推进需求、含调研的文案、静态预览、视频制作和导出；等待人工检查点，处理批注与下游失效。
---
# 视频工作流

## 环境与启动
从仓库根目录操作，Python 3.10+ 即可启动 UI：`python -m app.server --open`。只监听本机。运行 `python scripts/setup.py` 检查渲染所需 Node.js、FFmpeg、浏览器和锁定依赖；安装获准后运行 `python scripts/setup.py --install`。可用 BROWSER_PATH 指定浏览器，不要求用户提供模型 API。

默认项目 `workspace/`，样例 `examples/processed-meat/`。项目选择器独立查看二者。自定义项目使用 `--workspace path/to/project`，后续 CLI 和服务必须同一目录。

## 三种模式与真实执行桥接
详细接口和恢复策略见 `docs/workflow-modes.md`。五个阶段固定为 requirements、narration、preview、production、export。

- `manual`（全流程手动）：每阶段产物交给用户审核后再继续
- `semi`（半自动）：需求由用户确认；代理完成调研、文案、静态预览后停下等用户确认画面；随后自行制作并检查导出
- `auto`（全自动）：需求由用户确认；代理完成所有后续阶段并逐一实测审核，直到导出
- 需求始终由用户提交和确认。只有明示授权的测试兼容 `mode --self-review on`；不能把它当正常自动模式

网页保存状态和任务请求，不内置模型、不自动唤醒 Codex。启动 UI 后在**仍活跃的当前任务**运行 `python -m app.cli --workspace workspace wait --timeout 300`，它真正等待用户需求确认，不会因 nextAction 是 human 立即返回。收到 request 后读取最新状态，`claim --id ID --revision REV`，按 nextAction 执行直到当前模式的人工检查点或导出完成。到人工检查点提示用户看实际内容，再次运行有界 wait 等待批准。timeout 表示等待结束且没有自动唤醒承诺；提示用户回到当前 Codex 对话继续，不能假报已在生成。

每个阶段和每次写入前重新读取 status：
- 仅当前 request ID 可继续；取消、任务替换、模式变更后停止旧工作
- 代理 `save/artifact/submit/approve/revise/resolve` 带 `--task-id ID --revision REV`；每次成功写入后使用返回的新 revision
- `nextAction.actor=human` 就交还审核，不代替点击；若取消则保持暂停
- `nextAction.actor=agent` 执行真实工作或审核，不把 pending 说成完成
- 故障 `release --id ID --note 具体阻塞`，说明失败处及可恢复动作；不要重复领取后无穷重试

## 内容、版本与命令
状态存在 `.studio/workflow.json`，通过 CLI/UI 写入，不直接覆盖。

- `save --stage narration --file script.md` 保存文案；真实改动建立新版本并使下游失效
- `artifact --stage preview --path output/scene-01.png --label '建立问题' --role '开场问题'` 注册实际 workspace 内文件并复制至 `_artifacts/` 哈希路径
- `submit --stage preview` 检查前置批准、版本和实际媒体，进入审核
- `approve --stage narration --by agent --note '已阅读来源并对照数字、范围和完整口播稿'` 仅在模式允许处，写真实检查记录
- `revise --stage narration` 开始新版本；重新生成或核对并注册该版本产物
- `undo` 恢复上一状态快照，文件不删除；源码需另用 Git/项目内备份保护
- `mode --workflow-mode semi` 记录用户选择；更严格模式会重新打开必要人工审核，不沿用自动批准绕过检查
- `cancel --id ID` 暂停继续请求；`request` 明确恢复；不会谎称杀死外部渲染

不能使用 `--by human` 假装用户点击。仅用户对当前明确阶段已在对话批准时，才可代记，并在 note 写明批准内容。所有代理批准仍标记 agent。旧 `--stage research` 是 narration 的兼容别名，已经没有独立调研审核；新工作只用 narration。旧六阶段项目自动迁移，调研文字、产物、批注合并入文案，原状态/历史均保留。

## 五个阶段
1. requirements：收集目标、受众、画幅、平台、时长提示、上传参考资料、事实与语气边界。用户只需明确需求，不负责先做调研。
2. narration：读取 video-narration skill。先阅读需求和材料，主动查证关键结论、保留来源与限制，然后直接写成可讲述的完整口播稿。研究笔记放独立来源文件并注册于本阶段；不要要求用户另审「调研」。sources.json 可由 `python -m app.sources workspace/sources.json` 检查结构，但不能替代事实核对。按模式批准文案后再合成声音。
3. preview：自由创作 HTML 场景，渲染实际截图；按开场、关系解释、数据、限制、结尾等视觉角色选择代表画面，不固定三等分。注册真实 PNG/JPEG/WebP，并解释选择理由。模式需要人工审核时停在这里等待。
4. production：读取 annotations 的截图、时间、版本和归一化框选坐标处理反馈；不依赖固定元素 ID。制作动画、视频、字幕，使用无声阅读节奏或已选配音的真实音频时长。记录批注处理，不覆盖原意见。
5. export：实测视频时长、画幅、fps、字幕可读性、节奏、动画边界和可播放性；注册 MP4、字幕和必要源文件。未实测项明确说明。自动模式也不能跳过验证或拿文本代替视频。

## 时长、声音与视觉
时长 settings 支持 `durationMode=approx,duration=90` 或 `durationMode=range,durationMin=60,durationMax=180`。单位为秒，只是创作提示。按内容自然讲清楚；最终时间轴来自作者阅读时间或真实音频，不硬截到区间、不循环补空白、不强行改速凑数。偏离明显时解释内容取舍，不能伪称精确时长。

内置 23 种主题样图在 web/presets，5 种音色样音是已保存的本地 MP3，播放不联网调用 TTS。音色试听只是参考；Azure 选项下展示的也是标明来源的 Edge 样音。实际制作按用户选定 provider 合成。

创作场景前读取 requirements settings 的 themeId：`original` 从 styleDirection 自由创作；内置 ID 对照 `web/presets/themes.json` 并读取 `vendor/html-explainer/references/style-catalog.json` 对应主题的色彩、字体、材质和动效建议；`custom-` ID 对照当前状态 customThemes，读取 prompt、palette、previews，再结合 styleDirection。实际把选定视觉语言落实到场景代码，并在预览说明中写明采用哪些方向，不得把已选主题忽略成 UI 装饰。

配音读取 audio_mode、对应 edge_voice/azure_voice 和 rate；voicePresetId 只代表试听选择，真正合成以这些 provider 字段为准。执行 configure 后检查 project.json 同步一致；不能只换 voicePresetId 却保留旧合成声音。

原创方向始终可用；系列主题仅参考配色、字体、图形语言、动效节奏，不能强迫套版。自定义主题保存名称、说明、创作提示、配色、不可变预览图到当前项目，可导出/导入便携 JSON 主题包；不能写任意路径或覆盖内置库。

## 引擎与恢复
需求确认后、写场景前运行 `python scripts/engine.py configure workspace`，同步 width/height/fps/audio settings 到引擎 project.json，保留场景顺序与 slug，准备 GSAP/frames。时长是创作指导，不映射为强制渲染截断。原引擎 `vendor/html-explainer/` 保留来源/许可证，场景接口看其文档。

无声模式 `python scripts/silent_timeline.py workspace` 从 narration.json 的 id/text/duration/captions? 生成时间轴。配音见 docs/edge-tts.md 或 docs/azure-tts.md，用真实音频/词边界，文案或声音改变后重建下游。优先使用 `scripts/engine.py` 的 configure/synthesize/timeline/preview/render/layout 命令。

工作流文件受跨进程锁保护，网页刷新不会覆盖未保存输入。源码修改前另外备份，workflow undo 不会回写源码。旧状态迁移备份在项目内部，不删除；undo 读取旧快照时也自动迁移，旧研究材料不会丢失。
