# 叙 · Short Video Studio

一个与 Codex 协作的视频工作台：先把问题讲清楚，再确认画面，最后导出视频。

UI 负责输入、审核、批注和版本；Codex 负责调研、写稿、创作 HTML、渲染和检查。没有模型 API 配置，没有强制画面组件模板。当前默认是 **无声、带字幕视频**；语音生成暂缓。

## 新对话里开始

1. 克隆仓库并在 Codex 中打开这个项目目录
2. 在新对话里说：**我要制作视频了**
3. Codex 会读 `AGENTS.md` 和项目技能，检查环境，启动本地工作台并引导你确认需求

这依赖 Codex 实际打开仓库并读取项目说明，不是网页内置聊天机器人。网页的保存操作不会自动调用模型。

## 手动启动

Python 3.10+（Windows 可把 `python` 换成 `py -3`）：

```sh
python -m app.server --open
```

访问 http://127.0.0.1:8765 。UI 本身无第三方 Python 依赖。端口被占用可加 `--port 8766`。项目默认写入 `workspace/`；用 `--workspace path/to/project` 指定其他项目。

左侧可以切换到加工肉示例，默认新项目不会继承示例的自审模式。示例产物只在实际生成后显示。

## 渲染环境

```sh
python scripts/setup.py
python scripts/setup.py --install
```

需要 Python 3.10+、Node.js 20+、FFmpeg、Chrome/Chromium/Edge 和仓库锁定的 npm 依赖。检查脚本列出缺项，不会替你更改系统安全配置。浏览器不在常见路径时设置 `BROWSER_PATH`。

- Python：https://www.python.org/downloads/
- Node.js：https://nodejs.org/
- FFmpeg：https://ffmpeg.org/download.html
- Chrome：https://www.google.com/chrome/

首次装好软件后重新打开终端，使 PATH 生效。Windows 使用 PowerShell，macOS/Linux 使用终端。不要安装不明来源的“解码器包”。

```sh
python scripts/silent_timeline.py workspace
node vendor/html-explainer/scripts/render_video.mjs workspace --jpeg --jpeg-quality 95 --crf 18 --preset medium --concurrency 2
node vendor/html-explainer/scripts/check_layout.mjs workspace
```

先由 Codex 创建符合引擎接口的 project.json、narration.json 和场景 HTML，再执行渲染。原引擎及其说明位于 `vendor/html-explainer/`；仓库固定其来源版本，保留许可证。

## 创作顺序

需求沟通 → 资料调研 → 旁白文案 → 静态预览 → 视频制作 → 导出交付

- 正常项目每阶段提交后由你确认；明示授权的测试样片可以自审
- 回改前面内容会标记下游为“需要更新”，旧文件与历史记录保留
- 静态预览展示实际场景截图，按内容与视觉角色选择
- 图片和视频支持框选批注，保存原始截图、播放时间范围、版本、归一化区域坐标和文字意见
- 批注与作品分开存储，不要求生成代码带任何可编辑组件或固定元素 ID
- 支持撤销项目状态；不会删除已经生成的产物文件
- 系列主题包可选，原创视觉方向始终可用

## 文件边界

| 路径 | 用途 |
| --- | --- |
| `.studio/workflow.json` | 所选项目内的阶段、版本、批注和审核记录 |
| `.studio/history/` | 项目状态快照 |
| `annotations/` | 批注时捕获的 PNG 画面 |
| `project.json` / `narration.json` | 渲染引擎配置与讲述/字幕时间数据 |
| `app/` / `web/` | 无依赖服务端与前端 |
| `.agents/skills/` | 新 Codex 对话自动发现的项目工作法和原旁白技能 |
| `examples/processed-meat/` | 独立样例项目 |

所有产物注册路径必须位于当前项目内部。网页监听 127.0.0.1，写请求需要本次会话令牌并检查来源。不要把此开发工作台直接暴露到公网。

## Codex CLI

```sh
python -m app.cli --workspace workspace status
python -m app.cli --workspace workspace save --stage requirements --file brief.md
python -m app.cli --workspace workspace artifact --stage preview --path output/scene-01.png --label 开场 --role 建立问题
python -m app.cli --workspace workspace submit --stage requirements
```

自审仅在明确授权的项目上使用 `mode --self-review on`，随后 `approve --stage requirements --by agent --note 实际检查记录`。完整工作法见项目技能。结构化来源可运行 `python -m app.sources workspace/sources.json`，它检查字段和 URL 格式，不代替事实查证。

## 检查与排错

```sh
python -m unittest discover -s tests -v
```

- 页面打不开：查看服务终端是否仍在运行，检查端口、Python 版本
- 保存提示版本冲突：其他窗口或 Codex 已更新项目，刷新后再编辑
- 无法进入下一阶段：确认前置阶段已审核，下游过期内容已修订
- 找不到浏览器：设置 BROWSER_PATH 指向实际可执行文件
- 字幕或中文缺字：安装系统中文字体，再重新截图与渲染
- 视频失败：保留实际日志；UI 不会把失败任务显示为已经完成

应用不包含后台模型任务队列，也不会隐藏执行或自动支付。安全默认值是本地文件协作、明确审核和可追溯输出。

也可通过统一入口运行 `python scripts/engine.py timeline|preview|render|layout 项目目录`；具体参数看 `python scripts/engine.py --help`。注册产物时复制到项目 `_artifacts/` 的内容哈希路径，已审核截图不会被同名文件覆盖。撤销仅恢复工作流状态；修改 HTML/脚本前，Codex 应通过 Git 或显式备份保留源代码版本。

工作台配置区保存画幅、宽高、帧率、目标时长、视觉方向与制作备注，由 Codex 读取并落实到引擎。参考文件可直接从 UI 导入；支持文档、图片和视频，单文件上限 8 MB，大素材由 Codex 放入所选项目目录。UI 每 3 秒检查外部项目更新，保留未保存输入并提示冲突。

可选浏览器集成测试：`BROWSER_PATH=/实际浏览器路径 node tests/ui-smoke.cjs`。它使用隔离的临时项目测试配置、审核、保存冲突、素材上传、框选与截图，不修改用户项目。

需求配置确认后先运行 `python scripts/engine.py configure workspace`，将工作台的画幅与帧率落实到引擎；随后再创作场景并生成时间轴。目标时长、风格和制作备注由 Codex 在创作时遵守。

## 样片交付与复现

加工肉样片为 92.5 秒无声字幕视频，成片以会话附件交付。仓库保存完整场景源码、字幕、三张代表性预览和核验报告，MP4 与本地审核状态可通过制作流程重新生成。首次从仓库打开示例工作区时会建立新的审核状态。

运行示例目录内 README 的复现命令即可导出。仓库使用正常阶段审核，新制作任务按 UI 逐步确认。
