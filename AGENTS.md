# Codex：视频制作项目入口

用户说「我要制作视频了」或类似意图时，主动启动并完成下列流程，不只解释仓库。

1. 读取 [video-workflow](.agents/skills/video-workflow/SKILL.md)；写稿前读取 [video-narration](.agents/skills/video-narration/SKILL.md)。写稿及创作场景前读取 [文稿、图形讲解与成片验收](docs/creative-method.md)，按本次重点取舍内容、设计镜头内推进与全片连续视觉语言。
2. 确认当前目录和操作系统。运行 `python scripts/setup.py`（Windows 可用 `py -3`）。缺少 Python 时给官方安装指引。UI 仅需 Python 3.10+，无需先装渲染依赖。
3. 启动 `python -m app.server --open`，保留服务进程，检查 `http://127.0.0.1:8765/api/health`，告诉用户打开本机地址。端口占用时先检查是否本项目服务，否则用 `--port 8766`。不关闭无关进程。
4. 读取 `python -m app.cli status`，取返回的绝对 `workspace` 路径，后续命令固定传入该路径。让用户在需求页填写主题、受众、时长提示和参考资料，选择「全流程手动 / 半自动 / 全自动」，再提交需求。只有方向确实不足时才追问。
5. **保持当前 Codex 任务活跃，运行 `python -m app.cli --workspace PROJECT_PATH wait --timeout 300` 等待网页提交**。等待是本地文件观察；保存按钮和网页都不能唤醒已经空闲或关闭的 Codex。超时就清楚说明尚未生成，提示用户回到 Codex 说「继续当前视频项目」。不声称存在后台模型任务。
6. 收到请求后读取 `taskRequest.id`、`revision`、`nextAction`，用 `claim --id ID --revision REV` 领取。你是执行者：调研并直接写完整口播稿、创作、渲染、核验、注册产物；按已选择模式一直推进到**人工确认点或导出完成**。每次操作前重读状态，视频阶段代理写入带 `--task-id ID --revision REV`，遇到取消、请求替换、模式变更立即停止旧请求。发布包使用独立 `publishing.request.id` 与同一项目revision，按下条说明执行，不能混用两个任务ID。
7. 到人工确认点，告诉用户在网页看什么，并再次运行有界 `wait --timeout 300`，等待其批准后继续；不要把半自动停在「生成文案」，也不要把全自动停在「静态预览」。模式语义和完整命令见 `docs/workflow-modes.md`。
8. 最后导出还要主动准备发布包：视频标题、简介、话题，以及横版 **4:3** 和竖版 **3:4** 两张真实封面。读取 [发布包](docs/publishing-package.md) 与 [video-image-assets](.agents/skills/video-image-assets/SKILL.md)，按真实任务接口领取、保存和验证；不能把空表单、提示词或待处理请求说成已经生成。全自动在同一次执行中完成，不增加人工检查点；手动/半自动保留原来的导出审核语义。

## 重要边界
- 工作流保存五个阶段；手动/半自动显示需求沟通 → 文案（含调研）→ 静态预览 → 视频制作 → 导出。全自动显示四步：需求沟通 → 文案 → 视频制作 → 导出，跳过静态预览，不创建截图审核或伪造预览批准。需求始终由用户提交和确认。
- `manual` 每阶段人工审核；`semi` 需求和静态预览人工审核，其他阶段代理实测自审；`auto` 需求后跳过静态预览，文案批准后直接制作并检查成片直至导出。这来自用户明确选择，不可伪造 `--by human`。切换到更严格模式会重新打开必要人工检查点，并让下游失效。
- `mode --self-review on` 仅供用户明确授权的测试或样片，保留兼容；正常模式选择会关闭这一旧测试旁路。任何代理批准必须写真实检查记录，不能跳过实际内容/媒体验证。
- 时长仅是「约多少秒」或「多少至多少秒」的创作提示。根据内容、自然口播和真实音频决定实际时长，不强塞固定字数、不机械变速、不裁掉必要解释。
- 短视频突出用户指定的一件事并兑现开头，不自动全面介绍或追加习惯/替代建议；若用户明确要综合介绍，保留其必讲范围。【画面：】与口播按需分开，仅批准口播进入TTS。制作不擅自改词；先实际配音，再据真实时长/词边界安排字幕与关键画面，不虚报每个动作词级锁定。
- 图形表达关系、变化、比较与因果，镜头内有语义推进、跨镜头保留或变形主体。统一字体、核心palette、材质与标识，允许连续设计语言下的明暗变化。实际连续动画与编码抽帧检查活泼感、可读性和风格，技术测试绿不等于审美通过；无听审不声称听过。
- 默认无声带字幕；可选 Edge 或 Azure 配音。先批准文案再合成，使用真实音频/词边界生成字幕和时间轴。Edge 遵循 `docs/edge-tts.md`，Azure 遵循 `docs/azure-tts.md`。密钥只由用户在本机安全配置：允许用户本人在专用 Azure 凭据密码框输入并保存到 Windows 凭据管理器。代理不得主动检查或读取系统凭据库，不得执行取密钥/解密命令；仅可使用工作台无密钥状态接口或已授权的合成入口。代理禁止读取、回显、导出或代填实际密钥；禁止放入聊天、普通网页表单、项目文件、日志或 Git。macOS/Linux 不提供文件存储降级；同账号任意代码执行仍可能访问系统凭据，不能宣称密码框或加密可绝对隔离 AI。
- 内置主题样图和音色试听是仓库本地资产。主题是自由创作参考，不能变成强制模板。自定义主题保存在当前项目，可用主题包导出/导入跨项目复用。不要修改内置主题来保存用户私人素材。
- 允许自由 HTML/CSS/JS 视觉创作。不要引入强制组件库、固定元素 ID 或套版结构。
- 状态在 `workspace/.studio/workflow.json`，引擎配置在 `workspace/project.json`，不可混用。状态只能通过 CLI/UI 修改。
- 回改前置阶段必须让下游 stale 并重新核对。注册文件使用不可变快照；批注另存。undo 恢复状态，不会回写手工改过的源代码。
- 用户暂停请求只阻止下一次有检查的工作流写入，不代表已杀掉外部渲染进程。先检查状态，再决定是否可注册结果。
- 用户未授权安装或外部执行时，先检查环境并说明必要依赖；不修改其安全设置。使用官方 Python、Node、FFmpeg 和 Chrome/Chromium/Edge。
- 不提交密钥、私密素材、node_modules、用户 workspace 历史或缓存。发布前确认文件范围。
- 发布文案以本项目已确认的内容、重点和语气为依据，保留事实范围；不套泛化营销标题、不夸大风险，不自动发到任何第三方平台。用户编辑后保留其版本，只有明确重新生成才允许替换相应内容。
- 两张封面分别构图，沿用本片主题、字体与视觉语言；横版4:3、竖版3:4不是16:9/9:16。必须解码核验实际尺寸，并看手机小图的标题可读性、主体和裁切；只通过几何检查不能声称设计合格。原生生图需真实调用当前会话工具并登记来源；自由HTML/CSS渲染是另一条明确标识的路线，不能冒充生图模型。
- 只修改发布文字或封面不重做已验证的视频、TTS与时间轴。视频内容改变后提示发布材料可能过期，保留用户编辑和旧文件，核对后再明确更新。交付清单和项目包包含可读文案、两张图片及必要来源；不自动修改此前已交付的私人项目。

## 自由作曲与整片声音
- 背景音乐独立于配音：需求 `bgm_mode=none|ai|upload|preset`、`bgm_direction`、`bgm_upload`、`bgm_preset_id`。默认 none；silent 配音仍可有 BGM。没有音乐模型 API；由当前 Codex 自由创作任意 MIDI、编曲、源代码、分轨与 cue map。FluidSynth/FluidR3 GM 只提供真实采样演奏，不复制《初光》的固定旋律、结构或配器。
- 需求页“声音与音乐”统一试听、音量和组合预设。五条内置原创循环是约16–18秒短样，preset 模式重复到实际时间轴长度；不能称作另行创作的长曲。组合只在用户明确应用或创建新项目选用时改变设置，不自动覆盖旧项目；不保存凭据。规则见 `docs/audio-presets.md`。`voice_gain_db` 只改变混音，保持原 TTS 与时间轴；改变音色或语速才重新合成。浏览器试听与 FFmpeg 从 `web/presets/audio-mix.json` 读取共享基准、避让策略。
- 先运行 `python scripts/setup_bgm.py` 检查；依用户安装授权再运行 `--install-soundfont`。官方来源、许可证、校验与 Windows 指引见 `docs/bgm-setup.md`。网页不自动下载，不把音色库提交 Git。
- 当前项目路径：未指定 `--workspace` 的 `python -m app.cli status` 跟随网页当前项目；读取返回的 `workspace`，领取任务后所有命令固定传入该绝对路径。用户切换项目不能把进行中的制作写进另一项目。
- 内容与真实 TTS 决定镜头时长；音乐不能拉长视频、机械伸缩旁白。手动/半自动在静态预览阶段同时注册画面和音乐短样。全自动直接创作整曲、制作和核对成片，不要求静态图片或音乐短样审核，不新增阶段。
- `python scripts/engine.py bgm-prepare PROJECT --source music/original.mid --cues music/cues.json --retain-source music/compose.py --stem music/strings.wav`：所有输入在项目内；retain-source/stem 可重复。亦可用作者已混音 WAV，上传模式可省略 source 使用 bgm_upload。保留来源、分轨与 cue map，生成 `audio/bgm/full.wav` 整曲及 `audio/bgm/preview.wav` 15 秒试听。cue map 是 `[{"start":0,"end":10,"label":"开场"}]`。没有自动代写固定乐曲；需要代理完成真实创作。
- 按所选模式先批准文案，再 synthesize/timeline；音乐短样可独立制作。最终 `python scripts/engine.py soundtrack PROJECT` 仅从独立音乐、旁白和可选音效混音，严格按 layout 的 total_frames/fps 裁切/补静音/淡出，整曲按实测响度以单一固定增益向 -18 LUFS 归一化（真峰值不超过 -1.5 dBTP，高动态曲目优先保留峰值与动态），保留未改动原始来源；纯音乐默认原响度，有旁白自动 -12dB 并 ducking；bgm_gain_db 默认 0，表示额外增益偏移。可在引擎配置添加 `sound_effects:[{"path":"audio/hit.wav","start":1.2,"gain_db":-6}]`；不得把已混音文件再次当旁白。
- `render` 消费验证过的 `audio/soundtrack.wav`，即使无旁白；直接 renderer 和 mux-only 同样检查源/时间轴/设置哈希。源、方向、分轨、配音、时长等改变后重建相应下游，不重用旧片。注册 production/export 视频需保留渲染器同目录生成的 `.mp4.soundtrack.json` 验证记录。
- 导出注册整曲、最终混音、MIDI/创作源、cue map 与必要分轨；实际检查视频内音轨、旁白可懂度、尾部淡出与时长，不仅检查独立 WAV。本次运行环境若仅 Linux，必须明确 Windows 原生运行未实测。

## 主题资源包和图片创作
- 写场景前读取 `theme-packs/catalog.json`、选定包 manifest、相关 assets/shared 和 runnable preview。旧23主题仍可选，新增 `pack-` 主题对应资源包 ID。资源是可拆用的参考，允许组合、改写和新创作，不强制套版。
- 需要图片时读取 [video-image-assets](.agents/skills/video-image-assets/SKILL.md)。按 image_mode/image_direction 使用当前 Codex 实际生图能力，取得真实文件、验证、记录并用于 HTML。不得仅写提示词就声称图片完成，也不通过项目配置模型 API 或密钥。
- 用户明确指定的旁白、人物、音色、渠道、语速及所选预设优先。代理可以提前配置非秘密配音设置，使用 `app.cli voice`；Azure未指定音色时保留程序候选云帆多语言，不得用Edge冒充。云帆+40%不是全局默认，不能覆盖本次选择。配置不发起合成、不授权代确认需求；改变已批准的设置会重开需求并使下游失效。实际合成仍在文案批准后执行。
- 资源发现/复制使用 `app.theme_resources`（见 docs/theme-resource-tools.md）。先检索少量相关参考，查看真实动态效果，再按内容自由组合。不要把每个包全部塞入上下文。

- 需要更多视觉构思时，参考 `docs/visual-remix-guide.md`：按当前内容检索少量材料，先验证关键运动和代表帧，再自由扩展；这一指南不新增审核阶段。
- 可选动效、尊重用户主题的风格建议、封面检查和稳定续渲见 `docs/upstream-integration.md`。风格计划只供建议；使用原生 JS 动效时接入实际 `__tl` 契约。快门只按需显式启用，fps 改动后重建时间轴，续渲输入变更时完整重渲，沿用当前 manual/semi/auto 授权。
