# 可解释的画面建议与封面检查

本模块选择性移植 OneMoh/html-explainer v2.0.3 的 `style_director.py` 与封面文字检查，
保留原项目 MIT 许可。主题资源目录未替换；HTML/CSS/JS 仍由当前 Codex 原生创作。

## 建议如何参与创作

需求确认、文案完成并同步引擎后，可运行：

```sh
python scripts/engine.py style PROJECT
# 或直接调用；dry-run 不写文件
python vendor/html-explainer/scripts/style_director.py --project PROJECT --dry-run
python vendor/html-explainer/scripts/style_director.py --project PROJECT
```

输出 `style-plan.json` 和 `script/style-plan.md`。不修改主题、声音、工作流状态、HTML 或渲染设置。
`recommendation_only=true` 明示这是建议；`_motion` 也不会自动应用到渲染器。

- 读取 `.studio/workflow.json` 的 `themeId` 和 `styleDirection`，保留内置、素材包与自定义主题。
  自定义主题的 prompt、palette、预览与动态参考继续有效；`original` 保留自由创作方向。
- 每场 `primary` 是保留的用户主题；`suggested_primary` 是可借用的图形语法，
  `alternatives` 附评分和理由。角色、阅读节奏、数据与因果线索用于建议局部构图。
- `accent` 只建议局部数字、线型或关系图。字体、强调色和整体视觉方向应贯穿各场。
  可跨包重组、改写、创造新元素，无固定页面结构或必须套用的模板。
- `opener_variant`、`transition_out`、`motion_intensity` 可采纳、改写或省略。
  JSON 不会生成动画；作者需在真实时间轴中实现，并检查 seek、关键帧与跨镜头承接。
- `--pin scene=style` 固定的是该场可借用的语法；不会替换用户选择的主题。
  `--mood`、`--pace`、`--audience`、`--allow`、`--seed` 仅控制建议。

真实 layout 时长优先，其次 narration 中作者填写的 duration；最后才估算阅读时间。
风格建议不增加人工确认门，也不改变 manual / semi / auto 的授权规则。

## 封面检查与修复

独立创作 `frames/cover_169.html`（1920×1080）、`cover_34.html`（1080×1440）或
`cover_916.html`（1080×1920），按用户交付需求选用。

```sh
node vendor/html-explainer/scripts/check_cover.mjs PROJECT --only 34 --shot
node vendor/html-explainer/scripts/cover_build.mjs PROJECT --only 34
```

浏览器可从 `BROWSER_PATH` 或 `--browser PATH` 指定。检查用 1x 真实画布；导出默认 2x，
所以 3:4 的实际 PNG 是 2160×2880。旧 3:4 规格误写成 1440×1080（实际 4:3），
已有页面需修改宽高并重新排版；不会自动缩放或裁切源 HTML。

检查先冻结时间轴到终态，再量安全边距、字体、行宽、焦点与文字压叠。
钩子含 `<em>` / `<span>` 时读取完整句子，纯数字不会冒充标题。
可用 `h1`、`.hook` 或 `[data-cover-hook]` 标记短钩子。
不可见父元素下的文字不计入结果，竖版图表的小字号左右标签不误报成两栏正文。
文字溢出容器后互相压住也会失败；按 JSON 里的选择器与原因调整源码后重跑。
检查提供具体诊断，不自行覆盖作者的布局。

## 验证

```sh
python vendor/html-explainer/tests/test_style_director.py
python -m unittest discover -s tests -p test_style_advisory.py -v
node tests/cover-check-smoke.cjs
```

Windows Edge 实测：60 条上游风格断言、10 个原生主题/建议测试、8 份真实 HTML 封面；
确认嵌套强调、数字空格、祖先透明度、真实压叠、容器溢出、竖版小标签、短钩子与 3:4 比例。
PNG 文件头核验 1920×1080、1080×1440 及 builder 的 2160×2880 像素。
封面几何通过仍需检查事实、文案与缩略图效果，建议不承担成片质量评分。
