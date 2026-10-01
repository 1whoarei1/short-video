# 23 个可离线查看的视觉方向

工作台里的主题选择器使用仓库内已提交的 WebP 图片。首次克隆后，Python
启动本地工作台即可查看；不需要 Node、浏览器渲染依赖、字体下载或联网生成。

这些是基于上游配色、字体和图形语言，真实用 HTML/CSS/SVG 渲染的**静态概念示例**。
它们帮助比较视觉方向，并非用户项目的预览、动画效果保证或必须套用的版式。
「原创 / 自由设计」一直可用；选主题也可以按内容重新设计布局。

- [23 款总览图](../web/presets/themes/contact-sheet.jpg)
- [主题注册表](../web/presets/themes.json)
- [上游目录](../vendor/html-explainer/references/style-catalog.md)
- [逐主题来源、参考源码及配色](../web/presets/themes/source-evidence.json)
- [图片校验清单](../web/presets/themes/manifest.json)
- [浏览器离线与布局检查](../web/presets/themes/render-checks.json)

## 目录约定

注册表 `/presets/themes.json` 保留上游所有 23 个 `id`、`name` 和 `zh_name`，
顺序不变。中文显示名和简述方便检索，`category_id` 保留原分类。
`preview` 指向 1280 × 720 的本地 WebP；`preview_html` 是同画面可复现的 HTML。
Vignelli 原生为 9:16，示例把实际竖版画面完整放入横向预览，避免裁切误导。
Data Rollup 展示原生计数动画的静态终态，不把静态图片说成 Remotion 动画。

图表使用目录的真实分类计数，合计 23；小类汇总为「其他」。数字 5 表示本项目的
五个创作阶段。示例不编造产品业绩、市场数据或引用名人观点。

## 维护与复现

日常使用无需执行下列命令。只有修改目录样例时才需重新生成：

```sh
# 检查已经提交的资源；仅 Python 标准库
python scripts/verify_theme_previews.py
python -m unittest discover -s tests -p 'test_theme_previews.py'

# 重新构建 HTML 和注册表；仅 Python 标准库
python scripts/generate_theme_previews.py

# 重新渲染：使用仓库固定的 playwright-core、官方 Chrome/Chromium/Edge 与 Pillow
# 浏览器路径也可用 BROWSER_PATH 环境变量指定
python scripts/generate_theme_previews.py --render --browser /path/to/chromium
```

`render_theme_previews.mjs` 阻止全部 HTTP(S) 请求，等待本地字体加载，检查字体错误、
坏图、JavaScript 错误和文字越界，然后真正截图。Pillow 编码为 WebP 并生成总览图；
`verify_theme_previews.py --build` 解码每张图片，确认 1280 × 720、非空白、唯一哈希、
每张低于 200 KB，并保存校验清单。稳定的本地字体子集随仓库分发，所有许可证在
`web/presets/themes/fonts/`。

## 来源与边界

首要规范为项目固定版本的 html-explainer `style-catalog.json` 与 `.md`。
对目录中缺少细则的方向，同时阅读 nexu-io/open-design 的实际 HTML、composition
及 Data Rollup TSX 源码，提取真实配色与视觉特征。每个参考文件的固定链接与哈希
在 `source-evidence.json`；样例代码是本项目编写的独立静态实现。

风格来源包括 frontend-slides、huashu-design、HeyGen Hyperframes 与
Nate Herk 的 hyperframes-student-kit。原项目声明见
[第三方声明](../THIRD_PARTY_NOTICES.md) 和
[上游模板来源](https://github.com/nexu-io/html-video/blob/main/templates/NOTICE.md)。
上游目录版权信息按原样保留，不把风格预览视为对这些项目的代言。
