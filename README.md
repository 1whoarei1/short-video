# 叙 · Short Video Studio

与Codex协作制作HTML视频：工作台负责需求、审核、批注和版本；Codex负责研究、口播、自由HTML/CSS/JS创作、真实配音时序、渲染与验收。最后交付视频、可编辑的标题/简介/话题，以及横版4:3和竖版3:4封面。没有模型API配置或固定画面模板。

## 第一次使用

安装[Git](https://git-scm.com/downloads)和[官方Python](https://www.python.org/downloads/)，在PowerShell执行：

```powershell
git clone https://github.com/1whoarei1/short-video.git
cd short-video
py -3 scripts/setup.py
py -3 -m app.server --open
```

项目最低兼容Python 3.10；新安装选择官方仍受支持的版本。UI只需Python，无需先装齐渲染和配音依赖。`setup.py`缺渲染依赖时会返回1，但看到`UI: ready`仍可单独启动工作台。若没有`py`命令，使用本机实际Python解释器；安装与启动须使用同一解释器。完整依赖步骤和其他系统命令见[新机器设置](docs/new-machine-setup.md)。

在Codex中打开仓库目录，说**「我要制作视频了」**。它读取[项目入口](AGENTS.md)、[工作流技能](.agents/skills/video-workflow/SKILL.md)、[旁白技能](.agents/skills/video-narration/SKILL.md)和[图像技能](.agents/skills/video-image-assets/SKILL.md)。工作台地址为 http://127.0.0.1:8765；点击「＋开始新视频」，填写需求，选择模式并提交。

网页保存不会唤醒空闲Codex。保持当前任务活跃；中断后回到Codex说「继续当前视频项目」，或使用页面的「复制继续指令」。代理先读取`status`，领取任务后固定使用返回的项目路径，避免切换项目后写错视频。

## 以后启动与更新

在已有仓库目录运行：

```powershell
git status --short
git pull --ff-only
py -3 -m app.server --open
```

有本地修改或分支分歧时先处理自己的改动，不覆盖或强推。无需每次重新安装依赖；更新后需要制作视频时再运行`py -3 scripts/setup.py`。已有项目不随Git迁移，换电脑前备份整个workspace，见[项目管理](docs/projects.md)。端口被占用时确认是否已有本项目服务，否则用`--port 8766`，不关闭无关进程。

## 按用途补齐依赖

| 用途 | 需要什么 |
| --- | --- |
| 打开UI、编辑需求 | Python；无第三方Python依赖 |
| 浏览器预览、封面截图 | 兼容Node.js 20+；新安装选择官方仍受支持的LTS版及npm、锁定的playwright-core、实际安装的Chrome/Chromium/Edge |
| 视频编码与媒体验证 | 上述依赖，加FFmpeg和ffprobe |
| 登记图片与发布封面 | 当前Python环境中的Pillow；必须完整解码实际图片 |
| Edge配音 | 可选edge-tts包和网络；不需要Azure密钥 |
| Azure配音 | 可选官方SDK、用户的Speech资源和本机认证配置 |
| 采样原创音乐 | 可选FluidSynth和音色库；内置音乐试听不需要安装它们 |

依赖检查不证明实际渲染或在线合成成功。获准安装npm依赖后运行`py -3 scripts/setup.py --install`，它只安装锁定npm依赖，不安装Python包、浏览器、FFmpeg或模型。官方来源、`BROWSER_PATH`和分用途验收见[新机器设置](docs/new-machine-setup.md)。

Azure在每台新Windows电脑由用户本人进入「功能设置」→「Azure配音」填写密钥与区域，保存到系统凭据管理器。凭据不随Git、旧源码包或workspace迁移，不交给Codex。macOS/Linux不支持页面保存凭据，见[Azure说明](docs/azure-tts.md)。

## 制作与导出

手动/半自动：需求 → 文案（含研究）→ 静态预览 → 视频制作 → 导出。全自动跳过静态预览，需求确认后继续制作、检查并交付，无新增发布材料审核点。每种模式的批准规则见[工作流模式](docs/workflow-modes.md)。

默认无声带字幕，可选Edge/Azure与独立背景音乐；人物、音色、渠道、语速和所选主题由本项目设置决定。时长是创作提示，实际时间轴来自阅读节奏或真实配音。主题、图片与动效是自由组合的材料，不是强制模板，见[创作与验收参考](docs/creative-method.md)。

导出页可编辑保存、分项或全部复制标题/简介/话题；两张封面独立放大、下载、替换或明确重新生成。仅修改发布材料不重新制作视频或TTS；内容变化时提示材料可能过期并保留用户编辑。真实文件、来源记录、TXT/JSON、清单和项目包见[发布包](docs/publishing-package.md)。

## 功能与示例

| 内容 | 使用说明 |
| --- | --- |
| 15个主题素材包、23个动态风格方向 | [主题素材包](theme-packs/README.md)、[资源工具](docs/theme-resource-tools.md)、[自由材料改编](docs/visual-remix-guide.md) |
| 当前会话原生生图 | [图片素材](docs/image-assets.md)、[棱镜示例](examples/image-material-study/README.md)；以真实工具和已落盘文件为准 |
| Edge/Azure配音、真实声音时间轴 | [Edge](docs/edge-tts.md)、[Azure](docs/azure-tts.md)、[独立Edge技术样例](docs/reproduce-edge-sample.md) |
| 五条原创音乐循环、试听与声音组合 | [声音预设](docs/audio-presets.md)、[音乐工作台](docs/bgm-workbench.md)、[采样配置](docs/bgm-setup.md) |
| 自定义动态主题、便携主题包 | [动态主题](docs/custom-theme-animation.md) |
| 手机界面、图片与视频框选批注 | [小屏工作台](docs/mobile-layout.md)、[需求分组](docs/brief-groups.md) |
| 选择性移植的动效、风格建议与续渲 | [上游来源与用法](docs/upstream-integration.md)、[渲染稳定性](docs/renderer-stability.md) |
| 双封面与发布交付 | [发布包](docs/publishing-package.md)、[通用演示](examples/publishing-package-demo/README.md) |

工作台只监听本机。用户项目、凭据、缓存、node_modules及大型可选音色库不提交Git；第三方来源、许可证和素材记录保留在对应目录。仓库内容和本地产物边界见[目录说明](docs/repository-layout.md)。工作流撤销只恢复状态，不恢复手改源码，修改前另行备份。

## 检查与排错

```powershell
py -3 -m unittest discover -s tests -v
```

浏览器检查需准备上述依赖并设置真实`BROWSER_PATH`，例如`node tests/ui-smoke.cjs`。新检出的检查范围见[干净检出验收](docs/clean-checkout-verification.md)；发布功能既有实测见[发布验收](docs/publishing-validation-2026-10-06.md)。在线TTS、生图工具及新操作系统安装不能由离线测试替代。

完整回归另需从官方PyPI为测试解释器安装Pillow和numpy，安装命令见验收说明；这些不是打开UI的前置要求。

页面打不开先看服务终端和端口；版本冲突先保存自己的草稿并重读状态；缺图、缺字或渲染失败保留真实日志，不能把检查失败显示为完成。
