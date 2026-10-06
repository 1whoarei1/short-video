# 发布材料验收（2026-10-06）

以下是2026-10-06发布功能开发时的历史实测记录，不是之后每次提交的完整复验。使用隔离工作区、合成项目和通用演示数据；没有修改此前已交付的视频、用户图片或个人技能。没有调用真实TTS、生图服务或第三方发布平台。当前干净检出步骤见[验收说明](clean-checkout-verification.md)。

## 实际执行

- Windows原生Python 3.12、Chrome 154，已有Playwright依赖及FFmpeg 9.0.2。
- `python -m unittest discover -s tests -v`：282项，280项通过；2项Windows创建符号链接的测试因系统权限跳过。设置`BROWSER_PATH`，实际执行了HTML/声音混合/成片绑定测试。
- `node tests/publishing-ui-smoke.cjs`：15项实际浏览器操作检查通过；页面错误和外部请求均为0。
- `node tests/publishing-cover-smoke.cjs`：真实浏览器渲染、精确像素、2倍像素、重复seek/渲染、字体/图片就绪、文字几何、缺素材、外部资源及失败保留旧输出检查通过。
- 原有`ui-smoke.cjs`、`audio-presets-browser.cjs`和`bgm-ui-smoke.cjs`通过。实际视频播放、框选批注、音频播放、声音预设、音乐设置与390px界面仍可用。
- JavaScript语法、实际技能入口/Markdown链接与`git diff --check`通过。

发布UI检查包括文案保存与重载、原生剪贴板分项/全部复制、脏输入刷新保护、双封面放大/下载/替换、错比例与缺文件拒绝、真实TXT/JSON/ZIP下载、目标与方向请求、重复点击、取消、旧生成结果拒绝、过期提示、显式重新核对、切项目隔离及移动布局。发布操作保持原文案/制作版本与声音设置。

## 实际演示包

[通用示例](../examples/publishing-package-demo/README.md)横版为1600×1200，竖版为1200×1600；独立HTML分别使用并置柱图与上下增量分解。原图和400px缩略图已查看，标题清楚，来源登记为`code-generated` / `html-css-chromium`。

当时生成并检查了真实ZIP，包含标题、简介、话题、双封面、逐文件SHA-256清单、封面HTML与渲染报告，以及一段1080×1920、24fps、48帧、2秒的无声合成播放验收片。独立临时项目用公开的工作流和发布接口完成auto流程，最终`nextAction=complete`且`publishing.ready=true`；没有新增人工审核点。ZIP解压、每项哈希和视频全片解码通过。

仓库保留通用文案与独立封面源码，运行时ZIP、重复封面输出、哈希收据和状态不再作为检出必需文件。使用[示例复现说明](../examples/publishing-package-demo/README.md)重新构建，结果以本次真实生成文件和检查为准，不沿用历史包哈希。

准备好[渲染与图片依赖](new-machine-setup.md)后，从仓库根目录运行：

```powershell
py -3 examples/publishing-package-demo/build.py --browser 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

浏览器路径换成本机实际值，已设置`BROWSER_PATH`时可省略`--browser`。生成器每次创建独立且被Git忽略的`examples/publishing-package-demo/out/run-*`目录，输出真实双封面、合成播放视频、`verification.json`及该目录内`publishing/delivery/publishing-package.zip`。它不覆盖旧项目、不安装依赖、不调用TTS或生图服务；此公开合成样例使用明确的测试自审，不作为正常用户项目的审批旁路。

## 验收范围

真实生图服务未调用。本次验证的是自由HTML/CSS路线和真实文件登记；AI生成来源是作者声明，系统字节校验不能证明模型服务商。完成图片几何校验后仍需代理查看原图、小图和项目语义；程序不替代事实与审美审核。

网页保存发布请求，需要当前活跃Codex领取执行；网页不能唤醒已关闭或空闲的会话。ZIP包含当前已登记交付文件，必要源包需明确登记，不扫描整个私人项目。旧项目没有发布字段时保留既有导出语义，启用发布功能后才要求完整材料。
