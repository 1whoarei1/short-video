# 发布材料演示（非用户项目）

通用图形解释主题：比较增长时保留基期。100→150是演示数据，不指向真实机构或证券。两张封面使用同一字体、强调色与主题，横版采用文字与柱图并置，竖版采用上下排列的增量分解；它们是独立编写的HTML，没有裁同一张图。

```sh
node scripts/render_publish_covers.mjs examples/publishing-package-demo --browser /path/to/official/Chrome
```

实际产物位于`publish/`：`cover-landscape.png`（1600×1200，4:3）、`cover-portrait.png`（1200×1600，3:4）和验证报告`cover-render-report.json`。需要先按项目安装说明准备Playwright依赖及官方Chrome/Chromium/Edge；脚本不会安装软件或调用模型服务。

来源：本仓库作者编写的HTML/CSS与通用示意图，沿用本仓库许可；没有外部图片、用户私有素材或ImageGen产物。自动文字几何验证不等于完整审美审核：请同时检查400px缩略图中的标题、图形主体与独立构图。

完整实际交付示例为 [demo-package.zip](publish/demo-package.zip)，包含标题、简介、话题的TXT/JSON、两张封面、SHA-256清单、两份封面HTML及渲染报告，并收录一段1080×1920、24fps、48帧、2秒的无声合成播放验收视频。该视频用于验证交付和播放接口。所有素材都是本演示的通用数据与作者代码。

[text.json](publish/text.json) 是可编辑的文案输入；[publish.txt](publish/publish.txt)、[publish.json](publish/publish.json) 与 [manifest.json](publish/manifest.json) 是实际导出结果。ZIP内逐文件哈希及全片解码已验证。独立临时项目完成了auto文案→制作→发布请求领取→真实封面登记→导出流程，没有增加人工确认点；仓库不保存该临时项目的工作流历史。

按自己的实际项目内容重建发布包时，使用 [发布包流程](../../docs/publishing-package.md) 的请求、领取、文案/封面登记和完成命令。直接改本演示封面源文件后，需要重新渲染并重新登记对应输出。
