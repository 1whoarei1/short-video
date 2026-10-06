# 复现 Edge 云希 +40% 配音样片

本文只复现旧的独立技术样例，不代表新视频的内容、53/71/92.5秒长度、音色或语速默认。新制作按用户本次重点与项目设置执行 [创作与验收参考](creative-method.md)。

以下命令在刚克隆仓库的根目录执行，适用于 Python 3.10+、Node.js 20+、FFmpeg 和 Chrome/Chromium/Edge。Windows 可将 `python` 替换为 `py -3`。需要系统中文字体；浏览器不在常见位置时，按 README 设置 `BROWSER_PATH`。

原 `examples/processed-meat/` 仍是 92.5 秒无声样片。下面创建独立的 `workspace/edge-sample/`，不修改原文稿、场景、配置或字幕。目标目录已存在时复制命令会报错，避免覆盖之前的工作。

## 1. 准备依赖

```sh
python scripts/setup.py --install
python -m pip install edge-tts==7.2.8
```

先补齐 setup 报告的缺项再继续。`--install` 安装锁定的 npm 渲染依赖；不会安装操作系统软件。Edge 在线合成需要联网，不需要 Azure 密钥。此客户端是社区维护的可选包，不是 Azure 官方 SDK。

## 2. 建立独立副本并保存配音配置

以下 `python -c` 命令分别整行复制到终端；不依赖 Bash heredoc，也不依赖特定虚拟环境路径。

```sh
python -c "from pathlib import Path; import shutil; shutil.copytree('examples/processed-meat', 'workspace/edge-sample', ignore=shutil.ignore_patterns('.studio', '_artifacts', 'render', 'audio'))"
python -c "from pathlib import Path; import json; p=Path('workspace/edge-sample'); settings=dict(aspect='16:9',width=1920,height=1080,fps=24,duration=71,audio_mode='edge',edge_voice='zh-CN-YunxiNeural',edge_rate='+40%',styleDirection='保留原加工肉科普场景',qualityNote='真实音频与词边界决定时间轴'); (p/'edge-settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8'); (p/'edge-brief.md').write_text('沿用原样片文稿与场景，使用 Edge 默认云希，语速 +40%。按实际音频重新生成字幕与场景时长。',encoding='utf-8')"
python -m app.cli --workspace workspace/edge-sample save --stage requirements --file workspace/edge-sample/edge-brief.md --settings workspace/edge-sample/edge-settings.json
python scripts/engine.py configure workspace/edge-sample
```

这里的 `duration=71` 是约束/预期，不会强制拉伸音频。新的工作台审核状态仍需正常逐阶段确认；上述命令不会伪造批准或开启自审。

## 3. 合成、重建时间轴并导出

```sh
python scripts/engine.py synthesize workspace/edge-sample
python scripts/engine.py timeline workspace/edge-sample
python scripts/engine.py preview workspace/edge-sample --at 90
python scripts/engine.py render workspace/edge-sample --concurrency 2
```

查看全部预览后再执行 render。结果是 `workspace/edge-sample/out/processed-meat.mp4`，独立字幕为 `workspace/edge-sample/subtitles.srt`。要在工作台查看该副本：

```sh
python -m app.server --workspace workspace/edge-sample --open
```

`+40%` 只设置语音合成语速，没有对成片进行速度变换。脚本获取实际音频与逐词边界，再生成42段字幕及场景节拍；场景尾部对齐到24fps。改文稿、音色或语速后，重新执行 synthesize、timeline 和后续步骤。服务失败不会生成假语音或自动回退无声；每幕等待上限120秒。

## 4. 本次交付的实测结果

2026-09-30 的一次实际在线合成与导出结果：

- 音色 `zh-CN-YunxiNeural`，语速 `+40%`
- 12幕、42条字幕、1694帧；视频70.583333秒
- 1920×1080，24fps，H.264视频与24kHz单声道AAC音轨
- 文件3,803,576字节；AAC轨时长70.583000秒
- FFmpeg全片音视频解码零错误；音频均值−24.9dB、峰值−2.8dB
- 字幕显示相对真实边界的最大帧量化误差39.293ms，小于一帧
- 文稿和12幕HTML与原样片逐字节相同；只重建音频、字幕和时间轴

在线语音服务可能更新，同样参数再次合成的时长或文件字节数可能不同；以新生成的真实时间轴和实测值为准。

可以用以下命令检查新文件：

```sh
ffprobe -v error -show_streams -show_format -of json workspace/edge-sample/out/processed-meat.mp4
ffmpeg -v error -i workspace/edge-sample/out/processed-meat.mp4 -f null -
python scripts/engine.py layout workspace/edge-sample
```

本次检查了12幕90%时间点的浏览器截图，以及从最终MP4逐幕提取的字幕画面，没有发现明显裁切。未进行主观听音审查，不能把自动音轨/边界校验称作人工听审。

原场景包含全画布透明SVG容器。几何检查器按容器矩形推断遮挡，报告46项ERROR和29项WARN；实际截图未见其声称的整块文字遮挡。该检查不算通过，应结合实际画面逐项判断，不能仅靠返回码宣称画面有问题或已全部验证。事实核验数据见 [edge-QA.json](../examples/processed-meat/out/edge-QA.json)。
