# 新机器设置与日常启动

UI只需要Python；渲染、图片登记、配音与采样音乐按用途安装。最低兼容Python 3.10，新安装选择[Python官网](https://www.python.org/downloads/)仍受支持的版本。项目不自带其他电脑的凭据、用户workspace、依赖缓存或大型音色库。

## 首次：克隆并打开Codex

安装[Git](https://git-scm.com/downloads)及官方Python，按[Codex官方入门](https://developers.openai.com/codex/quickstart/)安装、登录本机客户端。在PowerShell执行：

```powershell
git clone https://github.com/1whoarei1/short-video.git
cd short-video
py -3 --version
py -3 scripts/setup.py
py -3 -m app.server --open
```

若没有`py`，改用本机已安装的Python解释器。安装包与启动服务始终使用同一解释器或虚拟环境。macOS/Linux对应命令通常为`python3 scripts/setup.py`及`python3 -m app.server --open`；这些是启动方法，不代表每个系统均已实测。没有桌面浏览器时省略`--open`。

`setup.py`只检查依赖；渲染缺项时返回1，但`UI: ready`表示可单独启动UI，不要将两条命令用`&&`绑定。工作台位于 http://127.0.0.1:8765，健康接口为 http://127.0.0.1:8765/api/health。端口已被本项目使用就复用现有服务，否则加`--port 8766`；不关闭其他程序。

在Codex打开仓库目录，说「我要制作视频了」。代理读取`AGENTS.md`和仓库技能，检查环境并实际执行任务。点击工作台「＋开始新视频」，填写需求、主题与声音选择，选择manual/semi/auto后确认。网页不启动模型或唤醒空闲Codex；保持任务活跃，中断后使用「复制继续指令」或回到对话说「继续当前视频项目」。领取后固定使用status返回的workspace，详见[工作流](workflow-modes.md)。

## 渲染和封面的依赖

| 依赖 | 官方来源与检查 |
| --- | --- |
| Node.js 20+及npm | [Node官网](https://nodejs.org/en/download)，新安装选择仍受支持的LTS版；`node --version`、`npm --version` |
| FFmpeg及ffprobe | [FFmpeg官方入口](https://ffmpeg.org/download.html)列出构建来源；`ffmpeg -version`、`ffprobe -version` |
| Chrome/Chromium/Edge | [Chrome](https://www.google.com/chrome/)或[Edge](https://www.microsoft.com/edge/download)；使用实际可执行文件 |
| playwright-core | 仓库package-lock锁定安装，使用官方npm registry；不额外下载浏览器 |
| Pillow | [官方安装说明](https://pillow.readthedocs.io/en/stable/installation/basic-installation.html)；仅图片/封面登记需要，UI不需要 |

安装软件后重新打开终端，使PATH生效。FFmpeg必须同时有ffprobe；封面HTML截图无需FFmpeg，但最终视频及媒体登记需要它。中文画面还需本机可用的中文字体。

用户确认安装后，在仓库根目录执行：

```powershell
py -3 scripts/setup.py --install
py -3 -m pip install --index-url https://pypi.org/simple Pillow
py -3 scripts/setup.py --json
```

`--install`只在`vendor/html-explainer/node`执行锁定的`npm ci --ignore-scripts`，使用npm官方registry；不安装Python包、FFmpeg、浏览器、音色库或模型。Windows通过官方Node安装旁的npm JavaScript入口执行，非标准布局缺入口时明确报错；可修复Node安装或在该目录手动执行`npm ci --ignore-scripts`。

JSON报告分别提供`ui.ready`、`render.ready`和`image_registration.ready`。Node执行版本检查，Pillow执行导入检查；其他可执行文件主要是路径发现，浏览器`launch_tested=false`。检查通过不能代替真实截图、编码或在线服务验证。默认检查不安装或下载，也不读取Azure凭据。

### 指定浏览器

自动发现失败时，在执行渲染的同一终端设置真实路径。不要填快捷方式、目录或包含引号字符的值。

```powershell
$env:BROWSER_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
py -3 scripts/setup.py
```

macOS示例为`export BROWSER_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'`；Linux改为本机实际Chrome/Chromium路径。这只影响该终端及其子进程，其他入口的Codex需使用自己的执行环境。无效显式路径会报未就绪；发现文件仍不证明浏览器能运行。

## 可选声音与生图

- 默认无声字幕无需TTS；背景音乐独立，silent仍可配音乐。
- Edge配音在当前Python环境安装可选edge-tts并使用网络，见[Edge说明](edge-tts.md)。安装不等于在线服务可用；发送的是已批准口播。
- Azure配音另需官方SDK及用户的Speech资源，见[Azure说明](azure-tts.md)。**每台新Windows电脑由用户本人**打开「功能设置」→「Azure配音」，填写密钥与区域，保存到系统凭据管理器；不要从旧源码包导入凭据，不交给Codex，不写项目或Git。保存不验证账户或调用合成。macOS/Linux不支持页面保存，由用户自行按说明配置执行进程环境。
- 五条内置原创音乐循环和预录音色随仓库提供，可离线试听。自由采样作曲先运行`py -3 scripts/setup_bgm.py`，按[采样配置](bgm-setup.md)获准后再安装FluidSynth和音色库；不是音乐模型或API。
- 原生生图取决于当前Codex实际提供的工具，Python/npm包和UI开关不能证明可用。没有工具就明确说明，继续使用授权素材或代码图形。真实文件、完整解码和来源登记见[图片素材](image-assets.md)及[双封面发布包](publishing-package.md)。

## 以后启动与换电脑

以后从仓库目录运行`py -3 -m app.server --open`即可，不必重新克隆、安装依赖或填凭据。需要更新先`git status --short`，无分歧且自己的修改已妥善保存后执行`git pull --ff-only`；若锁定依赖变化，再运行setup检查并按需安装。

继续旧视频应备份整个workspace，而非只拿MP4；项目索引、新视频、历史和素材在其中，见[项目管理](projects.md)。Git只迁移仓库资源，凭据必须在新电脑重新由用户配置。

## 实际能力验收

按用途完成：UI健康检查 → 新项目与需求保存 → 活跃Codex领取任务 → 真实图片登记（如使用）→ 浏览器代表帧 → 小段视频及ffprobe/完整解码 → 声音实际试听（如使用）→ 文案与双封面发布包。保留日志并明确未测项，不能以依赖ready代替执行成功。

当前检出和平台验证范围见[干净检出验收](clean-checkout-verification.md)；此前发布包测试使用Windows原生环境，见[发布验收](publishing-validation-2026-10-06.md)。这些记录不是全新操作系统安装认证，也不代表新Codex对话、真实Azure/Edge或原生生图已在每台机器验证。
