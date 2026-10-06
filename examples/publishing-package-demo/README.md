# 发布材料演示（非用户项目）

通用图形解释主题：比较增长时保留基期。100→150是演示数据，不指向真实机构或证券。两张封面使用同一字体、强调色与主题，横版采用文字与柱图并置，竖版采用上下排列的增量分解；它们是独立编写的HTML，没有裁同一张图。

## 新环境重建完整发布包

先按[新机器设置](../../docs/new-machine-setup.md)准备当前Python环境中的Pillow（`python -m pip install Pillow`）、本仓库锁定的Node依赖（`npm --prefix vendor/html-explainer/node ci`）、PATH中的Node/FFmpeg/ffprobe，以及已安装的官方Chrome/Chromium/Edge。无需模型服务、配音密钥或付费API；脚本不安装软件、不访问其他项目。

```sh
python examples/publishing-package-demo/build.py --browser /path/to/official/Chrome
```

也可以省略`--browser`，使用`BROWSER_PATH`或渲染器的官方浏览器探测。Windows可将`python`替换为已安装的`py -3`；安装Pillow与构建须用同一解释器。脚本使用当前Python进程的项目模块和当前仓库的Node依赖，不依赖旧工作区。每次在被忽略的`out/run-时间-随机值/`创建新项目，保留此前输出，不改演示源文件。

构建实际执行HTML封面渲染、图像解码、FFmpeg合成、ffprobe检查、全片解码，以及公开`Workflow`/publishing API的请求→领取→文案/双封面登记→完成→导出。合成演示显式启用`auto + selfReview`；这是运行脚本授权的样例自审，不能用于替代正常用户需求确认，也不伪记人工批准。

输出包括：

- `publish/cover-landscape.png`：1600×1200，4:3。
- `publish/cover-portrait.png`：1200×1600，3:4。
- `publish/cover-render-report.json`：实际字体、文字几何、解码尺寸与哈希检查。
- `synthetic-playback.mp4`：由真实竖封面合成的1080×1920、24fps、48帧、2秒无声播放验收文件；验证媒体交付，不是完整视频创作演示。
- `publishing/delivery/publishing-package.zip`：标题/简介/话题TXT和JSON、双封面、逐文件SHA-256清单及明确登记的视频、HTML、文案输入和渲染报告。构建重验包内每项哈希。
- `verification.json`：实际路径、环境、媒体参数及最终流程状态。命令结束也打印交付路径。

仓库保留[横版预览](publish/cover-landscape.png)、[竖版预览](publish/cover-portrait.png)、两份HTML及[可编辑文案输入](publish/text.json)。ZIP、导出TXT/JSON清单和运行报告按需重建，避免把同一素材重复保存在源码与压缩包内。技术几何通过不代替审美核对：修改设计后，请实际查看原图和400px缩略图中的标题、主体与裁切。

来源：本仓库作者编写的HTML/CSS与通用示意图，沿用本仓库许可；没有外部图片、用户私有素材或ImageGen产物。正常项目使用[发布包流程](../../docs/publishing-package.md)的实际创作、请求、领取和登记命令；不要套用本演示的文案或自审授权。
