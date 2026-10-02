# 山间来信

28 秒、1280×720、24 fps 的无声自由重组概念短片。没有配音、音乐、人物或模型 API；不会更改用户的声音选项。

信封始终是同一个画面主体：从雾里的山谷飞来，靠近后展开成一页不对称的纸上记忆，再折回、落在窗边。结尾“把远方，留在手边”由落下的信封完成，不是另接一张标题卡。

## 运行

在仓库内打开 `examples/mountain-letter/index.html`。支持离线素材、暂停、拖动，以及 `?t=14&controls=0` 定格。开发和渲染共用 `motion.js`；`frames/film.html` 只增加相对 base 和最小引擎适配器。

```sh
BROWSER_PATH=/tmp/chromium node tests/mountain-letter.cjs
BROWSER_PATH=/tmp/chromium python scripts/engine.py render examples/mountain-letter --concurrency 2
ffprobe -v error -show_streams -show_format -of json examples/mountain-letter/out/mountain-letter.mp4
ffmpeg -v error -i examples/mountain-letter/out/mountain-letter.mp4 -f null -
```

在其他机器使用实际已安装的官方 Chromium/Chrome 路径。测试使用仓库锁定的 `playwright-core`，不下载浏览器或依赖。测试 QA 文件默认写到操作系统临时目录下的 `mountain-letter-qa`，可用 `MOUNTAIN_LETTER_QA` 覆盖。视频和渲染帧由现有忽略规则排除。

## 自由重组的实际内容

- `cinematic-landscape`：实际山脊和松枝 SVG；重新取景，另写雾气、纸信路径与收尾窗台
- `tactile-archive`：只取光影台阶和植物版画，做一大一小的错位记忆页；没有保留原六格构图或时间轴
- `paper-craft`：实际折纸鸟 SVG，变成信内的小物件；没有借用整包预览
- `shared`：纸张颗粒、时间插值、三次路径、可选播放器和引擎适配器
- 新创作：信封及印章、连续展开/收拢、落点阴影、窗边构图、中文短句、全部 28 秒调度

资产与源码使用仓库相对路径，没有绝对作者机器路径。`provenance.json` 记录逐文件来源、SHA-256、用途及 MIT 许可证位置。示例可拆用的部件不要求任何固定场景 DSL、元素 ID 或人工填模板。画面为虚构插画，不是摄影、地理复原、真实手工折纸教程或个人经历记录。

## 本次实测

- 实际导出 H.264 MP4，28.000 秒，672 帧，1280×720，24 fps；无音频流
- FFmpeg 完整解码通过；另从 MP4 提取 3、14、27 秒三帧查看，涵盖飞信、记忆页和落信结尾
- 浏览器 6 个图像素材全部完成解码，零页面/请求错误
- 14 个代表时刻图像不同；反序重访 14 个相同时刻，截图 SHA-256 完全一致
- 检查时间钳制、28 秒接口、结尾收拢与到达状态
- 先查看三个资源包实际预览，再检查本片展开中、正文、收拢中和结尾；修正了中段植物纸片与文字间距
- 只在 Linux 官方 Chromium 环境实测，未实测 Windows 原生环境

这些结果证明本仓库资源可以自由组合成另一个实际短片；没有执行 GPT-6-Luna 对照实验，也不声称得到模型能力或质量提升的基准结论。当前作品由执行本任务的 Codex 原创编排，复用资源仍保留仓库贡献者署名。
