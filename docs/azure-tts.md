# Azure Speech 配音

本项目的 Azure 渠道使用微软官方 Speech 服务。工作台保存音色和语速，由 Codex 执行合成命令；保存配置本身不会发送语音请求。默认无声模式仍可直接使用。

## 免费层与账户

微软当前公布的 F0 神经语音免费额度为每月 50 万字符，实时合成限制为每 60 秒 20 次，单次音频最多 10 分钟。F0 不支持批量合成服务。使用前，在自己的 Azure 订阅里确认 Speech 资源的定价层是 **F0**。

程序无法仅凭密钥判断你的资源是否属于 F0，也无法知道其他程序已用了多少月额度。选择界面上的 Azure 并不会把 S0 资源变成免费资源。请在 Azure 门户核对资源、用量与计费信息，避免误用付费资源；项目不会自动创建资源或升级套餐。

- [官方价格](https://azure.microsoft.com/en-gb/pricing/details/speech/?cdn=disable)
- [官方配额](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits)
- [官方快速开始](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-text-to-speech)

资料核对日期：2026-09-30。微软可能调整额度和音色支持，以资源所在区域及官方页面为准。

## 本机准备

Azure 配音另需官方 Python 包 `azure-cognitiveservices-speech`（至少 1.21.0，建议使用当前稳定版）；无声模式不需要安装它。先在项目使用的 Python 环境中按官方文档安装该包，确认 FFmpeg、ffprobe 已在 PATH。

认证只由用户本人配置。每台新 Windows 电脑克隆仓库并启动工作台后，进入「功能设置」→「Azure 配音」→「Azure 密钥与区域设置」（也可从需求页 Azure 选项进入），输入资源密钥与区域，保存到 Windows 凭据管理器。无需配置 Windows 环境变量，后续合成会自动使用已保存凭据。凭据不随仓库迁移，每台电脑各自配置。保存会加密保存在当前 Windows 用户的本机凭据存储中，同一用户的所有视频项目共用，固定条目名为 `short-video/AzureSpeech/v1`。替换操作整体替换密钥与区域；删除也影响该用户的所有项目。不会在仓库、workspace 或浏览器存储中保存密钥，也没有密钥回读接口。密码框提交后立即清空，关闭、取消或离开页面也清空。保存不验证 Azure 账户，不发起付费请求。

本版本 macOS / Linux **不支持页面保存**；安全存储不可用或访问失败时拒绝保存，绝不退化为明文、项目密钥文件或自制加密文件。也可继续由用户自行在实际执行合成的进程环境中配置：

- `AZURE_SPEECH_KEY`：对应 Speech 资源密钥
- `AZURE_SPEECH_REGION`：资源区域标识，例如 `eastus`

两个环境变量必须一起设置，并且优先于凭据管理器；不混用不同来源的密钥与区域。删除已保存凭据不会删除环境变量。不要把实际密钥发给 AI，或放入普通项目表单、配置文件、命令参数与 Git。代理只查看状态；内部合成适配器直接取得凭据，不把密钥返回给代理、API 响应、缓存或清单。凭据存储访问异常会停止操作，不静默回退。

### 安全边界

Windows 凭据管理器提供静态加密与系统账号隔离，**不能阻止拥有同一系统账号任意代码执行权限的程序（包括 AI 工具）调用系统接口读取凭据**。没有声称对这类程序绝对保密。输入时避免 AI 浏览器操作、屏幕共享和录屏；浏览器扩展、调试工具及进程内存仍可能接触输入。页面使用仅回环地址 HTTP，凭据仅在本机浏览器与本机服务之间提交；不要通过公网代理、端口转发或远程嵌入页面输入。

服务只绑定 `127.0.0.1`，校验准确 Host/端口；凭据的状态、保存和删除均要求同源 Origin、JSON、短请求体及当前工作台令牌，不提供 CORS。项目资产使用沙箱策略阻止同源主动内容取得令牌；密钥不出现在页面回显或普通工作流历史。Python/SDK 必须短暂持有解密值，无法保证清除所有内存副本。

### 首次使用检查

自动化验收使用假密钥与内存存储；云 Linux 环境无法验证真实 Windows 凭据管理器。请在自己的 Windows 上先用自选的非秘密测试字符串（16–256 位字母、数字、短横线或下划线）和 eastus 手动保存，不运行合成；再刷新/重启工作台确认仍显示「已配置」且密码框为空，检查其他项目共用状态；删除后应不再显示存储来源（若环境变量仍在，则会明确显示）。测试后删除假凭据，再由你自己输入真实密钥。不要把密钥或截图发回 AI。真实 Azure 合成需在批准文稿与费用后自行验收。

首次合成会将已批准的旁白文本发送到微软 Speech 服务。仅发送自己授权处理的文本。不要为了测试而加入私人信息。

## 使用顺序

1. 需求阶段选择 Azure 配音、音色和语速；也可由代理提前配置非秘密语音选项，再由用户确认需求
2. 调研与文案阶段完成旁白，确认内容后运行引擎 configure，将设置同步到所选视频项目
3. 合成语音，收集音频和词边界；生成真实语音驱动的时间轴与字幕
4. 用实际场景时长创作动画；手动/半自动按静态预览检查点推进，全自动直接渲染并核对成片，再导出配音视频
5. 检查成片音频流、语音是否完整、字幕对应关系和画面节奏

Azure 默认候选是云帆多语言 `zh-CN-YunfanMultilingualNeural`（男声）；已有项目明确保存的音色保持优先。此音色可以根据输入文本自动识别多种语言，适合包含中文与英文名称的旁白。本项目保留原文并使用该音色合成，不通过翻译或替换成别的声音模拟多语言。仓库提供已授权生成的云帆中英文真实 Azure 试听（0%，约 13.6 秒）；播放与选择只读本地文件，不再次调用合成。音色与语言可用性仍以资源区域的官方列表为准。

核对日期：2026-10-05。参见微软 [音色与语言列表](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts) 和 [多语言自动识别说明](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice#adjust-speaking-languages)。

常见中文音色：晓晓 `zh-CN-XiaoxiaoNeural`、晓伊 `zh-CN-XiaoyiNeural`、云希 `zh-CN-YunxiNeural`、云健 `zh-CN-YunjianNeural`、云扬 `zh-CN-YunyangNeural`。音色可用性以所在区域官方列表为准。

- [音色列表](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts)
- [语速与 SSML](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-synthesis-markup-voice)

旁白的 `|` 是作者的字幕分段标记，不会读出来。带配音时不再沿用人工估计的静默字幕时间。更改文字、音色或语速后，应重新生成相应语音并核对画面；更改帧率也需重建时间轴。

## 错误处理

认证错误先检查资源区域和本机认证配置。429 可能来自请求频率、配额或某区域音色容量，不能一律判断为月额度用尽。等待后按错误提示重试，或在门户查看资源情况。不要把完整凭据或含凭据的日志贴出来。

词边界缺失、音频损坏或配音产物过期时应停止导出，先修复再继续。缓存和重试用于减少重复请求，仍应检查微软记录的实际用量。

## 验证范围

自动化测试可以验证设置、边界解析、音频时间轴和渲染管线。只有使用你自己的有效资源完成一次真实合成并试听，才能确认该账户的接入和音色实际效果。测试使用的模拟返回和合成音频夹具不能代替这一步。

Microsoft Edge 在线朗读及第三方 `edge-tts` 属于另一种接入方式，不属于这里的 Azure F0 渠道。

## 提前配置语音

代理可以在需求确认前设置配音服务、音色和语速；这一步不读取系统凭据，不发起合成，也不替用户确认需求。先读取最新状态和 revision，再运行：

```sh
python -m app.cli --workspace PROJECT status
python -m app.cli --workspace PROJECT voice --provider azure --voice zh-CN-YunfanMultilingualNeural --rate 0% --revision REV
python scripts/engine.py configure PROJECT
```

`voice` 只修改当前项目的非秘密配音设置，保留需求文字、尺寸、主题、音乐和其他服务的音色。`--provider` 可选 azure/edge/silent；语速范围为 -50% 至 +100%，负值使用 `--rate=-10%`。已领取任务时带 `--task-id ID`；旧任务、过期 revision 和取消后的写入都会被拒绝。已有的用户明确声音选择优先，未经新授权不能覆盖。

修改已确认的声音会重新打开需求确认，并将后续阶段标为需要更新。配置同步后仍须批准文案，才执行 synthesize/timeline；不会因为提前配置就发送未批准文本。密钥与区域仍由用户在专用凭据设置中填写，不能通过 voice 参数传入或写进项目。云帆只支持 Azure 入口，不自动回退到 Edge。

## 命令入口

```sh
python -m pip install "azure-cognitiveservices-speech>=1.21.0"
python scripts/engine.py configure workspace
python scripts/engine.py synthesize workspace
python scripts/engine.py timeline workspace
# 手动/半自动需要静态预览；全自动省略本行
python scripts/engine.py preview workspace
python scripts/engine.py render workspace
```

将 `workspace` 换成实际视频项目目录。先保存工作台配音设置，再运行 configure。首次使用依赖需按本机权限完成安装。合成不代替文案审核；确认文稿后再发送。
