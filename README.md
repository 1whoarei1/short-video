# 叙 · Short Video Studio

选择性吸收 html-explainer v2.0.3：可选动效、尊重用户主题的风格建议、封面检查修复和稳定续渲。保持原生 HTML/CSS/JS 创作及三种工作流，详见 [使用与来源记录](docs/upstream-integration.md)。

一个与 Codex 协作的视频工作台：先把问题讲清楚，再确认画面，最后导出视频。

UI 负责输入、审核、批注和版本；Codex 负责调研、写稿、创作 HTML、渲染和检查。没有模型 API 配置，没有强制画面组件模板。默认制作 **无声、带字幕视频**，也可选择 **Microsoft Edge 或 Azure Speech 配音**，按真实音频时间生成字幕和场景时长。接入说明见 [Edge TTS](docs/edge-tts.md) 和 [Azure TTS](docs/azure-tts.md)。

## 新对话里开始

1. 克隆仓库并在 Codex 中打开这个项目目录
2. 在新对话里说：**我要制作视频了**
3. Codex 会读 `AGENTS.md` 和项目技能，检查环境，启动本地工作台并引导你确认需求

这依赖 Codex 实际打开仓库并读取项目说明。网页不调用模型、也不能唤醒空闲对话；活跃 Codex 先运行 `python -m app.cli status` 获取当前视频的 `workspace` 路径，再使用 `python -m app.cli --workspace PROJECT_PATH wait --timeout 300` 等待你确认需求，收到请求后按模式继续到人工检查点或导出。领取任务后固定使用该路径，避免切换项目时写错视频。等待超时可回到 Codex 说「继续当前视频项目」。详见 [运行模式与文件桥接](docs/workflow-modes.md)。

换电脑或首次配置时，按 [新机器启动与能力检查](docs/new-machine-setup.md) 操作。手机界面适配说明见 [小屏工作台](docs/mobile-layout.md)。

## 手动启动

Python 3.10+（Windows 可把 `python` 换成 `py -3`）：

```sh
python -m app.server --open
```

访问 http://127.0.0.1:8765 。UI 本身无第三方 Python 依赖。端口被占用可加 `--port 8766`。项目默认写入 `workspace/`；用 `--workspace path/to/project` 指定其他项目。

点击 **＋开始新视频**，填写名称即可创建空白项目；用左侧下拉菜单切换视频。每支视频有独立的需求、素材、阶段、批注与历史，创建新视频不会清空旧项目。工作台会记住当前选择，已有标签页仍固定显示自己的项目。新项目保存在默认工作区的 `.studio/projects/` 下，不提交到 Git。也可切换到加工肉示例；新项目不继承示例的自审模式，示例产物只在实际生成后显示。

## 背景音乐

项目切换与备份的详细说明见 [开始新视频](docs/projects.md)。

需求页可选择 **不使用背景音乐 / AI 原创·真实采样音色 / 使用我的音乐**。
背景音乐与旁白独立，纯字幕视频也可有 BGM。AI 自由编写 MIDI、乐谱或创作源，
通过 FluidSynth 和 FluidR3 GM 采样音色演奏；可先听短样，再完成整曲与最终混音。
也可上传有权使用的 WAV、MP3、M4A、OGG 或 FLAC（最多 32 MiB / 60 分钟）。
手动/半自动的音乐试听融入静态预览；全自动跳过短样审核，直接完成整曲、混音和成片。

首次使用采样作曲，运行 `python scripts/setup_bgm.py` 检查可选依赖；
明确安装后用 `--install-soundfont` 下载经过校验的约 142 MiB 音色库。
音乐模型、GPU 和音乐 API 密钥不是这一方案的依赖。
渲染器按视频的真实时长混合旁白、音乐和可选音效，支持人声避让、片尾淡出，
并拒绝过期音轨。参见 [工作台使用](docs/bgm-workbench.md) 和 [采样环境安装](docs/bgm-setup.md)。

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

手动/半自动：需求沟通 → 文案（AI 调研并写口播稿）→ 静态预览 → 视频制作 → 导出交付

全自动：需求沟通 → 文案 → 视频制作 → 导出交付

- 全流程手动：每阶段由你确认；半自动：需求和静态预览由你确认；全自动：确认需求后跳过静态预览，直接制作并检查最终视频
- 时长支持约数或区间，只是创作提示；以内容、自然口播和真实音频决定实际时间
- 调研合并到文案，需求页可直接上传参考资料；无需单独审核调研阶段
- 回改前面内容会标记下游为“需要更新”，旧文件与历史记录保留
- 手动/半自动的静态预览展示实际场景截图，按内容与视觉角色选择
- 图片和视频支持框选批注，保存原始截图、播放时间范围、版本、归一化区域坐标和文字意见
- 批注与作品分开存储，不要求生成代码带任何可编辑组件或固定元素 ID
- 支持撤销项目状态；不会删除已经生成的产物文件
- 内置 23 个系列主题的本地短动画、概念样图，以及 5 种标准中文音色的本地试听和 Azure 云帆的真实中英文试听，首次打开即可浏览，不触发在线生成
- Azure 支持云帆多语言 `zh-CN-YunfanMultilingualNeural`；代理可提前用 `app.cli voice` 配置服务、音色和语速，不读取密钥或立即合成，见 [Azure 配音](docs/azure-tts.md)
- 自定义主题保存在当前项目，可导出/导入含图片和可选短视频的主题包跨项目复用；原创视觉方向始终可用

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
python -m app.cli --workspace workspace wait --timeout 300
```

运行模式用 `mode --workflow-mode manual|semi|auto` 记录用户选择；需求仍由用户提交和确认。代理后续写入使用任务 ID 和最新 revision，详见 [执行约定](docs/workflow-modes.md)。测试自审仅在明确授权的项目上使用 `mode --self-review on`，随后 `approve --stage requirements --by agent --note 实际检查记录`。完整工作法见项目技能。结构化来源可运行 `python -m app.sources workspace/sources.json`，它检查字段和 URL 格式，不代替事实查证。

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

也可通过统一入口运行 `python scripts/engine.py synthesize|timeline|preview|render|layout 项目目录`；具体参数看 `python scripts/engine.py --help`。注册产物时复制到项目 `_artifacts/` 的内容哈希路径，已审核截图不会被同名文件覆盖。撤销仅恢复工作流状态；修改 HTML/脚本前，Codex 应通过 Git 或显式备份保留源代码版本。

工作台配置区保存画幅、宽高、帧率、目标时长、视觉方向与制作备注，由 Codex 读取并落实到引擎。参考文件可直接从 UI 导入；支持文档、图片和视频，单文件上限 8 MB，大素材由 Codex 放入所选项目目录。UI 每 3 秒检查外部项目更新，保留未保存输入并提示冲突。

可选浏览器集成测试：`BROWSER_PATH=/实际浏览器路径 node tests/ui-smoke.cjs`。它使用隔离的临时项目测试配置、审核、保存冲突、素材上传、框选与截图，不修改用户项目。

需求配置确认后先运行 `python scripts/engine.py configure workspace`，将工作台的画幅与帧率落实到引擎；随后再创作场景并生成时间轴。目标时长、风格和制作备注由 Codex 在创作时遵守。

## 样片交付与复现

加工肉样片为 92.5 秒无声字幕视频，成片以会话附件交付。仓库保存完整场景源码、字幕、三张代表性预览和核验报告，MP4 与本地审核状态可通过制作流程重新生成。首次从仓库打开示例工作区时会建立新的审核状态。

运行示例目录内 README 的复现命令即可导出。仓库使用正常阶段审核，新制作任务按 UI 逐步确认。

## 配音模式

工作台的需求配置可选择无声、Edge 或 Azure。Edge 默认云希，Azure 默认晓晓；音色和语速分别保存。音频产物可直接在工作台试听。修改配音设置后会沿用现有流程标记后续内容需要更新。

- Edge：免 Azure 密钥，需联网及可选 edge-tts 包。加工肉配音示范使用云希、语速 +40%
- Azure：可选官方 SDK，使用你自己的 Speech F0 资源及本机安全配置。项目无法验证资源层级或剩余额度
- 配音流程：configure → synthesize → timeline → preview/render。实际语音时间决定每幕长度与字幕，缓存可复用未变化的配音

[Azure 本机配置](docs/azure-tts.md) · [Edge 接入说明](docs/edge-tts.md) · [复现 +40% 配音样片](docs/reproduce-edge-sample.md)

可选配音 UI 测试：`BROWSER_PATH=/实际浏览器路径 node tests/voice-ui-smoke.cjs`，覆盖模式切换、独立语速、旧项目兼容与手机宽度。试听调速专项测试：`BROWSER_PATH=/实际浏览器路径 node tests/voice-speed-ui-smoke.cjs`，覆盖播放中调速、保持音调、五个样本、服务独立设置与保存、手机滑块和离线请求检查。Azure 接口的离线测试使用模拟 SDK；真实账号合成需你完成本机配置后验证。

### Azure 本机凭据

每台新 Windows 电脑首次使用：克隆仓库 → 启动工作台 →「功能设置」→「Azure 配音」→ 输入密钥和区域 → 保存。也可从需求页 Azure 选项进入。用户本人保存后，程序会自动使用，无需设置 Windows 环境变量。凭据不会随 Git 迁移，每台电脑需单独配置。密钥与区域存入系统凭据管理器，不写项目文件、不回显。macOS/Linux 暂不支持页面保存，仍可使用用户自行配置的环境变量。系统静态加密不能隔离拥有同一账号任意代码执行权限的 AI/程序；安全边界和首次使用检查见 [Azure 配置](docs/azure-tts.md)。

凭据离线验收：`BROWSER_PATH=/实际浏览器路径 node tests/credentials-ui-smoke.cjs` 使用内存假凭据检查保存、替换、删除、取消及密码清空。`node tests/credential-asset-security-smoke.cjs`（同样设置 BROWSER_PATH）检查恶意项目资产隔离与图片/视频功能。这些测试不会操作真实系统凭据或请求 Azure；Windows 原生存储需按上面的首次使用检查单验收。

## 主题素材包与原生生图

现在视觉选择器提供 **15 个资源素材包 + 23 个风格动效方向**。悬停或键盘聚焦可播放短动画，选定后继续动态预览。素材包内有可拆用 SVG、共享材质/动效源码、改编说明和实际可运行的 HTML；AI 可以跨包组合并自由创作。见 [主题资源包](theme-packs/README.md)。

需求页“图片素材创作”允许当前 Codex 按需生图。项目提供素材规划、验证和存储流程，真正生图使用会话实际可用工具，**不配置模型 API**。操作说明见 [图片素材](docs/image-assets.md)；实际原生生图结合 HTML 的例子见 [玻璃棱镜实验](examples/image-material-study/README.md)。

本轮记录与后续重点：[第一轮迭代](docs/iterations/2026-10-02-round-01.md)。

资源查找和安全复制：[Codex 资源工具](docs/theme-resource-tools.md)。主题卡片的“放大播放与查看素材”适用于手机和桌面，可先查看动画与素材再选用。

需求页已分为“内容与资料 / 画面与声音 / 交付偏好”三个可任选的分组，保留未保存输入，全部仍属于一次需求确认。详见 [需求页分组](docs/brief-groups.md)。主题包可使用共享叙事动效与跨包素材自由组合。

自定义主题支持短 MP4/WebM 动态参考及便携 JSON 导入导出，详见 [自定义动态主题](docs/custom-theme-animation.md)。实际原生生图与跨资源重组案例见 [草莓视觉实验](examples/strawberry-remix/README.md)。

材料怎么真正用于新画面，见 [自由材料改编指南](docs/visual-remix-guide.md)。新机器验收的实际范围见 [干净检出验证](docs/clean-checkout-verification.md)。

本次材料扩展的成品、使用步骤和实测范围见 [迭代验收指南](docs/overnight-delivery-guide.md)。
