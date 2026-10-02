# 换电脑后第一次启动

克隆项目后可以先打开工作台、填写需求；不用先装齐渲染、配音、图片或音乐依赖。UI 只需要 Python 3.10+。建议新电脑使用官方仍受支持的 Python 版本。

## 1. 克隆 → 在 Codex 打开目录

安装 [Git](https://git-scm.com/downloads) 与 [Python](https://www.python.org/downloads/)，按 [Codex 官方入门](https://developers.openai.com/codex/quickstart/) 安装和登录适合本机的客户端：

```sh
git clone https://github.com/1whoarei1/short-video.git
cd short-video
```

在 Codex 中打开这个目录，并说「我要制作视频了」。Codex 应读取 `AGENTS.md`，检查环境，再启动 UI。克隆不包含其他电脑的私密素材、项目历史、凭据、npm 缓存或音色库；继续旧项目需另行备份和迁移自己的项目，见 [项目管理](projects.md)。

## 2. 先检查，再打开 UI

Windows PowerShell：

```powershell
py -3 --version
py -3 scripts/setup.py
py -3 -m app.server --open
```

macOS / Linux：

```sh
python3 --version
python3 scripts/setup.py
python3 -m app.server --open
```

若 `python` 已指向 Python 3.10+，也可使用 `python`。安装与启动始终使用同一个解释器/虚拟环境。访问本机 http://127.0.0.1:8765；健康检查是 http://127.0.0.1:8765/api/health。没有桌面浏览器时不传 `--open`，不要把服务暴露到公网。

缺少渲染依赖时检查脚本仍返回退出码 1，这是原有兼容行为，**不表示 UI 无法启动**；看 `UI: ready` 后单独执行启动命令，不要用 `&&` 把 UI 绑在完整检查成功之后。端口被占用时先确认是否已经是本项目服务；否则加 `--port 8766` 并访问新端口，不关闭无关进程。

机器可读报告：`python3 scripts/setup.py --json`（Windows：`py -3 scripts/setup.py --json`）。`ui.ready`、`render.ready`、`image_registration.ready` 分别回答不同问题。`render.ready` 只是依赖检查通过，不是成功渲染证明。`render.checks.browser.launch_tested` 始终为 false；ffmpeg/ffprobe/npm 是路径发现，Node 执行版本检查，Pillow 执行导入检查。可选语音包只有安装元数据，不证明凭据、网络或服务正常。默认检查不安装软件、不下载浏览器或模型，也不读取 Azure 凭据。

## 3. UI → 功能设置 → 当前视频需求

1. 点击「＋开始新视频」并起名，确认左侧当前项目正确。
2. 打开「功能设置」。需要 Azure 配音时由用户本人在专用设置中配置；Windows 使用系统凭据管理器，每台新电脑单独配置。不要把密钥交给 Codex、写入项目或 Git。macOS/Linux 不支持页面保存凭据，见 [Azure 配音](azure-tts.md)。默认无声字幕无需语音服务。
3. 在需求页填写主题、受众、时长提示与参考资料，选择主题参考、图片需求、背景音乐以及「全流程手动 / 半自动 / 全自动」。旁白、人物、音色和语速由你选择；补依赖、换主题或生成图片不应改写这些选择。
4. 提交需求，保持当前 Codex 任务活跃。Codex 按所选模式研究、写稿、制作并在必要处等待审核，见 [流程模式](workflow-modes.md)。网页保存不能唤醒已关闭或空闲的 Codex；等待超时或中断后，回到 Codex 说「继续当前视频项目」。

## 4. 按用途补依赖

- **视频渲染**：Node.js 20+、npm、FFmpeg **及 ffprobe**、Chrome/Chromium/Edge，以及锁定的 playwright-core。从 [Node 官方下载](https://nodejs.org/en/download)、[FFmpeg 官方下载入口](https://ffmpeg.org/download.html)、[Chrome 官网](https://www.google.com/chrome/) 或 [Edge 官网](https://www.microsoft.com/edge/download) 取得适合系统的软件。FFmpeg 官方入口说明可用构建来源；不要装不明“解码器包”。安装后重新打开终端，确认 `node --version`、`ffmpeg -version`、`ffprobe -version`。只有 ffmpeg 不足以完成媒体验证。
- **真实图片登记**：当前 Python 环境需要 Pillow；UI 不需要它。依照 [Pillow 官方说明](https://pillow.readthedocs.io/en/stable/installation/basic-installation.html)，用户批准安装后执行 `python3 -m pip install Pillow`（Windows 对应 `py -3 -m pip install Pillow`）。缺少或无法导入 Pillow 时不能绕过图片解码验证。见 [图片素材](image-assets.md)。
- **语音**：Edge 或 Azure 的包、网络和凭据检查独立于 UI，见 [Edge 配音](edge-tts.md) 与 [Azure 配音](azure-tts.md)。安装包不等于真实合成已经成功。
- **采样音乐**：运行 `python3 scripts/setup_bgm.py`，再按 [音乐配置](bgm-setup.md) 在授权后安装。FluidSynth 与音色库是演奏工具，不是音乐生成模型。

用户确认安装 npm 依赖后，在仓库根目录运行 `python3 scripts/setup.py --install`，Windows 对应 `py -3 scripts/setup.py --install`。这仅在 `vendor/html-explainer/node` 执行锁定的 `npm ci --ignore-scripts`，使用 npm 官方 registry；不会安装 Python 包、FFmpeg、浏览器、音色库或模型。

Windows 会发现 `npm.cmd`，用同目录官方 npm CLI 的 JavaScript 入口通过 Node 执行，避免把 `.cmd` 当原生可执行文件或启用 shell；非标准 npm 布局缺少入口时明确报错，可修复官方 Node 安装或手工在该目录执行 `npm ci --ignore-scripts`。`--install --json` 的 npm 日志发往 stderr，stdout 保持一个 JSON 报告。

### BROWSER_PATH 示例

填实际存在的浏览器可执行文件，不是快捷方式或安装目录。下面引号只是 shell 语法，不要把引号字符存进变量值。变量只影响当前终端及从中启动的进程；从其他入口运行 Codex 时需在对应执行环境设置。

Windows PowerShell：

```powershell
$env:BROWSER_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
py -3 scripts/setup.py
```

Windows cmd：

```bat
set "BROWSER_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
py -3 scripts/setup.py
```

macOS：

```sh
export BROWSER_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
python3 scripts/setup.py
```

Linux（替换成本机真实路径）：

```sh
export BROWSER_PATH='/usr/bin/chromium'
python3 scripts/setup.py
```

显式设置无效路径会显示未就绪，不会默默把另一个浏览器当作该配置已验证。发现文件仍不保证能启动或截图；首次代表帧预览和完整渲染才验证运行能力。不要为通过检查关闭浏览器沙箱、操作系统安全机制或安装未知来源程序。

## 5. 能力边界与新机验收

- 生图取决于**当前 Codex 会话实际提供的工具和权限**。不要根据 GPT 型号名、Python 包、npm 包或设置开关宣称原生生图可用。项目不配置模型 API/密钥，也不会由 UI 自动启动模型。
- 生成计划或提示词不是已生成图片。必须取得真实文件，解码、登记不可变快照，放进画面并检查代表帧；没有生图工具时如实说明，用授权的已有素材或代码图形继续。
- 新机验收：UI 健康检查 → 新项目需求保存 → 当前会话领取任务 → 一张真实图片登记（如使用）→ 一帧浏览器预览 → 一段视频及 ffprobe 验证 → 实际配音/音乐试听（如使用）。不能以依赖检查代替这些步骤。
- 本轮覆盖 Linux 实际依赖检查，以及 Windows/npm 路径和 macOS 浏览器发现的模拟单元测试。**未在 Windows/macOS 原生系统完成启动或渲染验收**；模拟通过不代表原生平台已验证。
