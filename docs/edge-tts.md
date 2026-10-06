# Microsoft Edge 在线朗读配音

这是通过第三方开源 Python 包 `edge-tts` 使用 Microsoft Edge 在线朗读服务的渠道。它不需要 Azure 密钥；服务可用性和限流由远端决定，不具有 Azure F0 的免费额度承诺。

- [edge-tts 原始项目](https://github.com/rany2/edge-tts)
- [PyPI 包](https://pypi.org/project/edge-tts/)

在项目 Python 环境中从官方 PyPI 安装 `edge-tts`。选择工作台的 Edge 配音模式，默认中文音色为云希 `zh-CN-YunxiNeural`，可调整语速。比如 +40% 表示向语音服务请求加快语速，不会把整段视频简单加速。

确认文案后，Codex 执行合成与时间轴命令。旁白正文会发送给微软在线朗读服务；仅合成你授权处理的内容。原文中的 `|` 用于字幕分段，不朗读分隔符。

时间轴使用实际生成的音频与词边界。更改旁白、音色或语速后重建音频与字幕，再核对动画。无声模式仍可使用；Edge 服务不可用时应保留失败信息，由用户选择稍后重试或切换已配置的 Azure，不会悄悄切换服务。

旧Edge独立复现样例使用云希、语速+40%，仅说明该例配置。新制作读取本项目或用户明确选用的组合，不将+40%固定为默认；本地试听变速与实际TTS节奏/停顿不同。实际生成与核验结果记录于项目；文档中的配置本身不代表合成成功。

## 命令入口

```sh
python -m pip install "edge-tts>=7.2.8"
python scripts/engine.py configure workspace
python scripts/engine.py synthesize workspace
python scripts/engine.py timeline workspace
python scripts/engine.py preview workspace
python scripts/engine.py render workspace
```

将 `workspace` 换成实际视频项目目录。先保存工作台配音设置，再运行 configure。首次使用依赖需按本机权限完成安装。合成不代替文案审核；确认文稿后再发送。
