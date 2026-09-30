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

认证由用户在自己的运行环境中安全配置：

- `AZURE_SPEECH_KEY`：对应 Speech 资源密钥
- `AZURE_SPEECH_REGION`：资源区域标识，例如 `eastus`

让运行 Codex/合成命令的进程能够读取这两个环境变量。不要把实际密钥发给 AI、填入工作台、写入项目目录中的配置文件或提交到 Git；项目目录内的文件可能经本地预览服务提供访问。环境变量的配置由你自行完成。代码不会将密钥放入缓存或清单。

首次合成会将已批准的旁白文本发送到微软 Speech 服务。仅发送自己授权处理的文本。不要为了测试而加入私人信息。

## 使用顺序

1. 需求阶段选择 Azure 配音、中文音色和语速，保存并确认
2. 调研与文案阶段完成旁白，确认内容后运行引擎 configure，将设置同步到所选视频项目
3. 合成语音，收集音频和词边界；生成真实语音驱动的时间轴与字幕
4. 用实际场景时长创作动画，预览、审核，再导出配音视频
5. 检查成片音频流、语音是否完整、字幕对应关系和画面节奏

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

## 命令入口

```sh
python -m pip install "azure-cognitiveservices-speech>=1.21.0"
python scripts/engine.py configure workspace
python scripts/engine.py synthesize workspace
python scripts/engine.py timeline workspace
python scripts/engine.py preview workspace
python scripts/engine.py render workspace
```

将 `workspace` 换成实际视频项目目录。先保存工作台配音设置，再运行 configure。首次使用依赖需按本机权限完成安装。合成不代替文案审核；确认文稿后再发送。
