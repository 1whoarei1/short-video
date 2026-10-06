# 可选：复现Edge公开技术样例

此页只复用仓库内公开加工肉示例，验证Edge配音和真实音频时间轴。样例音色云希、语速+40%不是新项目默认，也不代表新的文稿或固定时长。正常创作按[工作流技能](../.agents/skills/video-workflow/SKILL.md)和[创作参考](creative-method.md)执行。

先按[新机器设置](new-machine-setup.md)准备Node/npm、锁定playwright-core、FFmpeg/ffprobe、官方浏览器与中文字体。只在确认公开示例文本、同意联网合成后继续；安装可选社区客户端不会验证服务可用性：

```powershell
py -3 -m pip install --index-url https://pypi.org/simple "edge-tts>=7.2.8"
```

## 建立独立副本

从仓库根目录执行，不修改公开示例或已有用户项目。目标已存在时`copytree`会拒绝覆盖：

```powershell
py -3 -c "import shutil; shutil.copytree('examples/processed-meat', 'workspace/edge-sample', ignore=shutil.ignore_patterns('.studio', '_artifacts', 'render', 'audio', 'out'))"
py -3 -c "from pathlib import Path; import json; p=Path('workspace/edge-sample'); settings=dict(aspect='16:9',width=1920,height=1080,fps=24,durationMode='approx',duration=71,audio_mode='edge',edge_voice='zh-CN-YunxiNeural',edge_rate='+40%',styleDirection='保留公开示例场景',qualityNote='实际音频决定时间轴'); (p/'edge-settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8'); (p/'edge-brief.md').write_text('独立Edge技术复现；使用公开示例文稿与场景，云希+40%，按实际音频重新生成字幕与场景时长。',encoding='utf-8')"
py -3 -m app.cli --workspace workspace/edge-sample save --stage requirements --file workspace/edge-sample/edge-brief.md --settings workspace/edge-sample/edge-settings.json
```

需求与文稿仍按选择的工作流确认；这些复制/配置命令不批准需求或开启自审。`duration=71`只是提示，不伸缩配音或截断视频。下面是确认文稿后使用的低层引擎命令，不代替工作台阶段审核或最终发布包。

## 合成与验证

```powershell
py -3 scripts/engine.py configure workspace/edge-sample
py -3 scripts/engine.py synthesize workspace/edge-sample
py -3 scripts/engine.py timeline workspace/edge-sample
py -3 scripts/engine.py preview workspace/edge-sample --at 90
py -3 scripts/engine.py render workspace/edge-sample
ffprobe -v error -show_streams -show_format -of json workspace/edge-sample/out/processed-meat.mp4
ffmpeg -v error -i workspace/edge-sample/out/processed-meat.mp4 -f null -
```

在渲染前检查代表帧；最终查看并试听成片，核对字幕、音轨和时长。Edge脚本获取真实音频与词边界，失败不伪造声音或自动切换无声。改文本、音色或语速后重建相应音频和时间轴；更改fps也需重建时间轴。预览与编码后的画面要一起检查，几何检查报告不能替代实际可读性。

查看独立副本可运行`py -3 -m app.server --workspace workspace/edge-sample --open`。macOS/Linux用实际的`python3`解释器；本页命令不是各平台或当前在线服务已成功的声明。

## 历史技术结果

2026-09-30曾在上述音色/语速下导出12幕、42条字幕、1694帧、70.583333秒的1920×1080/24fps H.264/AAC视频；音视频全片解码通过，未进行主观听审。历史公开核验数据见[edge-QA.json](../examples/processed-meat/out/edge-QA.json)。远端服务可能变化，当前结果须重新测量，不能依旧时长或哈希宣称本次成功。
