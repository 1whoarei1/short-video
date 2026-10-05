# 上游能力的选择性移植

本项目保留 html-explainer `842c695`（v1.4.3）作为基础，选择吸收截至 `820a295`（v2.0.3）的动效、风格建议、封面检查和渲染恢复能力。`vendor/html-explainer/UPSTREAM_COMMIT` 仍表示基础版本，`UPSTREAM_SELECTION.json` 记录每个模块的来源与改编；没有声明整包同步。MIT 许可证和原第三方许可继续保留。

## 原生创作和动效

HTML/CSS/JS 仍是主底层。`motion.js` 提供可选的计数、图表、路径、镜头、轨道、切换等局部运动，不生成固定场景。`configure` 给新项目复制 GSAP 和 motion.js；已有修改过的 motion.js 不会被覆盖。原 15 主题素材包、23 动态预览、原生生图和口播 skill 继续使用。

参考 [可运行因果运动示例](../examples/causal-motion/README.md) 与 [动效接口](../vendor/html-explainer/references/motion-library.md)。示例包含数字主角、逐步建图、原因标注、结论和主体跨镜头承接。先让观众看见“谁发生了什么变化”，再按需要拆用动效。跨镜头承接由作者实际编写；风格计划里的转场文字不会生成动画。

渲染器和 lint 的接口为 `window.__tl`。原生 JS 的 `window.__seek(t)` 必须经过 GSAP 长度载体或可选的 `theme-packs/shared/engine-bridge.js` 适配；仅写 `__seek` 不够。倒序取样和重复取样应返回同一画面。motion 示例的参数可以任意改写，示例镜头长度不限制实际内容。

## 只提供建议的风格导演

```sh
python scripts/engine.py style PROJECT --dry-run
python scripts/engine.py style PROJECT
```

读取当前 narration/layout 和工作台选定主题，输出候选、评分理由、局部借用方式、动效强度和承接建议。正常运行生成 `style-plan.json` 与 `script/style-plan.md`；dry-run 只输出文字。用户选择的内置、素材包、自定义主题保持为主方向，原创主题按创作说明自由组合。这个命令不修改 workflow、project.json 或场景，也不自动开启快门。用户人物、声音、语速与自然口语仍优先。

## 封面

```sh
python scripts/engine.py cover PROJECT
python scripts/engine.py cover PROJECT --only 916
```

保留生成器和检查器的接口，补上真实钩子识别、文字墨迹重叠和竖屏双栏检查。`34` 的构建与检查尺寸统一为 **1080×1440（3:4）**；原来误写的 1440×1080 是 4:3。已有旧比例封面需重新构建再检查。检查失败应改对应 HTML 后重新构建；检查器不会擅自改写文案。

## 保守渲染和恢复

```sh
python scripts/engine.py render PROJECT
python scripts/engine.py render PROJECT --profile balanced --resume
python scripts/engine.py render PROJECT --profile final --shutter 180 --samples 4
```

默认使用项目 fps、现有 JPEG 输出，单浏览器，不启用快门。指定 profile 后使用该档位的截图/编码参数，避免入口的旧 JPEG/crf/preset 覆盖档位。profile 可选 `legacy/draft/balanced/final/master`；不因建议的 motion_intensity 自动开启快门。`--shutter` 仅在明确需要时启用，多采样会增加耗时；先验证关键两三秒再制作长片。`--workers`、`--recycle` 和 `--quality` 为明确的资源/分辨率选择。

帧缓存与源文件、素材、声音、时间轴、渲染参数绑定。`--resume` 只续用匹配且完整的帧，输入改变后拒绝复用旧缓存。浏览器进程重启只用于可恢复故障，不能掩盖缺图或不符合时间轴契约的场景。

工作台改变 fps 后，`configure` 删除旧 layout/subs/beats，必须重新执行 `timeline`。静态图片和成片的实际尺寸仍要核验，设备缩放由页面上下文及 CDP 的有效 scale 控制。

本项目特有的无声排除旧旁白、缺配音硬失败、BGM/SFX 新鲜度、渲染中输入不变和 soundtrack 哈希绑定继续保留。无声字幕可以独立配 BGM；最终是否有声音轨取决于当前配置，而非目录里是否残留 MP3。

## 工作流与验证

不采用上游每阶段强制人工确认的 gate_check。`manual/semi/auto` 保持原授权语义，最新 auto 跳过静态预览，制作阶段内部检查后直接导出；阶段回改仍使下游失效，不伪造人工批准。

运行基础回归与新增模块检查：

```sh
python -m unittest discover -s tests -v
node vendor/html-explainer/tests/test_motion.mjs
python vendor/html-explainer/tests/test_style_director.py
node tests/causal-motion.cjs
node tests/renderer-stability.cjs
node tests/cover-check-smoke.cjs
node tests/ui-smoke.cjs
```

浏览器测试需安装锁定 Playwright 依赖并设置实际 `BROWSER_PATH`。本次真实运行结果见 [验收记录](upstream-validation-2026-10-05.md)。仓库新增 GitHub Actions，按推送提交运行回归和真实 HTML 渲染；本地实测仍单独记录。
