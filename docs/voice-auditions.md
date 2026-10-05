# 预置音色试听

五个标准中文音色的试听 MP3 随仓库保存。克隆后，启动本地工作台即可播放；点击试听只读取本地静态文件，不需要联网、安装 `edge-tts`、配置 Azure 或等待实时合成。

| 音色 | 声音 | 服务标识 |
| --- | --- | --- |
| 晓晓 | 女声 | `zh-CN-XiaoxiaoNeural` |
| 晓伊 | 女声 | `zh-CN-XiaoyiNeural` |
| 云希 | 男声 | `zh-CN-YunxiNeural` |
| 云健 | 男声 | `zh-CN-YunjianNeural` |
| 云扬 | 男声 | `zh-CN-YunyangNeural` |

这五个 Edge 样本使用相同文本，以正常语速 `0%` 录制，便于比较：

> 你好，欢迎来到视频创作工作台。选一个喜欢的声音，把每一个想法讲清楚，让故事更有温度。

这些样本由 **Microsoft Edge 在线朗读**生成。Azure 的同名音色选项可以播放它们作为 **Edge 参考试听**，但不能将其称为 Azure 生成的音频。服务、版本、语速及实际文稿都可能改变最终表现；预置样本不能证明 Azure 账号可用，也不代表当前项目已生成配音。自定义音色没有对应预置样本时，应明确显示未提供试听，不能冒用其他音色。

界面的简短音色描述只是选用参考。描述参考了 Edge 返回的音色标签，不代表试听开启了某种情绪、角色或 SSML 风格。

Azure 还可选择云帆多语言 `zh-CN-YunfanMultilingualNeural`。它使用 2026-10-05 经用户授权生成的真实 Azure 试听：正常语速 0%，约 13.6 秒，包含上述中文文本与英文 “Hello, welcome to the video studio.”。源音频为 24 kHz 单声道 PCM，仓库保存 128 kb/s MP3；完整解码及真实词边界检查通过。它只在 Azure 选项显示，不放入 Edge 列表，播放与选择不会再发起 Azure 请求。

## 文件和前端契约

- `web/presets/voices.json`：版本 `schemaVersion: 1`，包含统一文本、生成日期、服务来源和五个 `voices` 条目
- `web/presets/azure-voices.json`：独立的 Azure 音色目录，包含适用服务、Azure 实录来源、试听文本、日期、音频哈希及解码指标；重新生成五个 Edge 样本不会覆盖它
- `web/presets/voices/<服务标识>.mp3`：24 kHz、单声道、48 kb/s 的服务原始 MP3，没有转码或加速
- `web/presets/voices/zh-CN-YunfanMultilingualNeural.mp3`：独立的真实 Azure 中英文录音
- 静态地址：`/presets/voices.json` 与 `/presets/voices/<服务标识>.mp3`
- 每个条目有 `id`、`name`、`gender`、`description`、`locale`、`sampleUrl`、`sampleVoice`、`sampleProvider`、`sampleRate`、`sampleText` 和实测 `durationSeconds`
- `durationSeconds` 为 MP3 容器时长；另存完整解码时长 `decodedDurationSeconds`、大小、SHA-256、峰值、均方根音量及完整词边界末尾时间，便于复核
- `sampleRate` 是语速字符串 `0%`，采样频率另用 `sampleRateHz: 24000`

样本生成日期与客户端版本是可追溯信息；重新生成后远端模型可能更新，不保证字节完全相同。仓库样本保持原始正常语速，不随项目设置改写。

## 试听调速

试听窗口的「试听语速」默认读取当前服务的语速，可在 `-50%` 至 `+100%`（`0.50×` 至 `2.00×`）之间逐 1% 调节，也可「恢复正常」。播放中调整立即生效，不重新合成、重新载入音频或发起外部请求；五个样本共用此速度，切换播放时仍只保留一个声音。

滑块与需求页当前服务的语速字段同步，Edge 和 Azure 各自独立。关闭窗口、切换音色会保留未保存的语速；点击需求页「保存」后按现有项目流程持久化，重新打开试听仍使用该服务的设置。仅打开试听或播放不会产生未保存修改。需求页输入无效语速时，试听暂用正常速度并显示说明，调节滑块可修正；保存仍遵循原来的范围校验。

前端使用音频元素的 `playbackRate` 与 `defaultPlaybackRate`，并在浏览器支持时启用 `preservesPitch`（兼容旧前缀）保持音调。这个调节只改变本地样本播放速度，不能精确模拟 TTS 在指定语速下的节奏、停顿或韵律；正式配音仍按所选服务和语速合成。

## 离线核验

需要 Python 3.10+、FFmpeg 与 FFprobe；不需要第三方 Python 包或网络：

```sh
python scripts/generate_voice_auditions.py --check
```

省略参数也只执行核验。检查覆盖五个音色及元数据、8–12 秒时长、MP3 全量解码、24 kHz 单声道、非空音量、浮点解码峰值低于满幅、文件哈希及词边界末尾时间。这些是技术检测，不是主观听感评分或逐字人工试听。

## 明确联网重新生成

仅维护者需要执行；普通使用者无需运行。先按 [Edge 接入说明](edge-tts.md) 安装可选的官方 PyPI `edge-tts` 包（此批样本使用 7.2.8）：

```sh
python scripts/generate_voice_auditions.py --generate
python scripts/generate_voice_auditions.py --check
```

`--generate` 会把上面的固定公共示例文本发送给 Microsoft Edge 在线朗读服务，不读取或发送项目正文，不使用 Azure 密钥。它先从实际服务列表核对五个标识、语言和声音性别，再逐个合成。使用系统/客户端的证书验证；设置了 `SSL_CERT_FILE` 时加载指定的可信 CA 包，不关闭 TLS 或主机名验证。

语音列表请求最多等待 45 秒，每次合成最多 120 秒。只有五个临时样本均生成成功、词边界完整且音频核验通过后，才替换仓库中的样本和清单；服务不可用时失败退出，不会换用其他音色或服务。生成的新 MP3 和清单需要随代码一起提交，页面才能在新克隆中直接试听。
