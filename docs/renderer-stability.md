# 稳定渲染、配置与续渲

保留 HTML/CSS/JS 场景和 `window.__tl.pause(t, false)` 时间轴契约。逐帧 seek 同时同步 CSS 动画、字幕与进度条；图片先 decode，缺图或缺时间轴直接失败。制作流程和用户授权模式仍由工作台负责，渲染器不增加人工审核。

本模块选择性借鉴 html-explainer v2.0.3（`820a295eb8d285f9023c715fe6cf6d0f31e03e45`）的配置档位、快门线性光积分、超时重试和续渲思路，保留上游 MIT 许可。`blur_integrate.py` 来自该提交；`render_video.mjs` 在本项目原渲染器上改造，未整包覆盖。23 主题不因本模块改变。

## 配置与实际像素

```sh
node vendor/html-explainer/scripts/render_video.mjs PROJECT --list-profiles
node vendor/html-explainer/scripts/render_video.mjs PROJECT --profile balanced --concurrency 2
node vendor/html-explainer/scripts/render_video.mjs PROJECT --quality 2k --keep-frames
```

默认 `legacy`，保持项目 fps/尺寸、关闭快门，默认一个浏览器；`draft/balanced/final/master` 只建议截图与编码质量，均不偷偷开启快门、改 fps 或升到 4K。`--quality 1080p|2k|4k` 按项目高度算缩放，保持逻辑布局和宽高比；`--scale` 显式覆盖它。页面 context 接收 `deviceScaleFactor`，CDP clip 接收相同有效 scale，每张实际 PNG/JPEG 的尺寸会再校验。探测的 Chrome/Edge 路径显式传给浏览器启动参数。

`--workers N` 指定独立浏览器上限，默认 1；兼容的 `--concurrency N` 只给它加上更小的上限，不会把 workers 1 增加到 2。上限最多 8，实际不超过场景数；单场景按帧顺序 seek。`--recycle 150` 默认每 150 帧重建浏览器；0 可关闭。截图超时默认 60 秒（`HX_SHOT_TIMEOUT_MS` 可调整，下限 1 秒），当前帧最多重试两次，先关旧浏览器再清理半帧。不是上游按帧分配给六个浏览器的默认路径。

改变 fps 后必须配置并重建 timeline/subs/soundtrack。直接传 `--fps` 与 `layout._total.fps` 或字幕 fps 不一致会失败，不沿用旧 total_frames。显式 fps 与新的时间轴一致时支持 60 fps。

## 续渲与输入一致性

```sh
node vendor/html-explainer/scripts/render_video.mjs PROJECT --resume
node vendor/html-explainer/scripts/render_video.mjs PROJECT --mux-only
node vendor/html-explainer/scripts/render_video.mjs PROJECT --only scene-03
```

`render/checkpoint.json` 绑定场景 HTML、项目内素材/音乐/配音/字幕/时间轴等源文件内容、工作台设置、渲染器与积分器代码、profile/fps/尺寸/截图通道/快门设置，并记录每张完整帧的 SHA-256。已存在且哈希匹配的帧才可复用；丢失或损坏的帧由 `--resume` 重截。输入或截图设置改变时，以上三种缓存命令均拒绝运行，应不带它们完整重渲。`--only` 用于补帧，不再允许改 HTML 后混用其他场景旧帧。编码 crf/preset 可通过 mux-only 修改，因为截图内容不受它们影响。

渲染中在场景/浏览器回收边界、合成前后复核输入。`render/renderer.lock` 排除同一项目并行渲染。生成目录 `render/out/output`、工作台历史及本次显式 `--out` 的视频和两个 sidecar 不作为普通源文件；实际从它们加载的项目内文件会另记 dependency 哈希并验证，`_artifacts` 内容也纳入源文件哈希。素材应放 frames/assets/audio/music 等源目录。远程 HTTP 字体/脚本/图片和项目外 file:// 资源不进行外部扫描；一旦实际加载，当前 checkpoint 会禁止缓存复用，请先将依赖本地化到项目内。更改任意其他源文件会保守地要求完整重渲。

音频保护继续生效：silent 排除旧旁白；Edge/Azure 缺配音硬失败；BGM/SFX 混音必须通过原 soundtrack 新鲜度检查；合成后生成原有 `.mp4.soundtrack.json`，绑定视频与真实 soundtrack 哈希。新增 `.mp4.render.json` 记录实测截图尺寸、fps、总帧数、复用帧数、快门覆盖与重试次数。

## 按需快门

```sh
node vendor/html-explainer/scripts/render_video.mjs PROJECT --shutter 180 --samples 8 --shutter-only scene-02,scene-05
```

仅在显式开启时采样，角度 0–360、样本数 1–32。每帧在当前场景范围内采样 PNG，使用上游 numpy/Pillow 线性光积分与硬切保护，再按原截图通道输出。需要 Python、numpy、Pillow；不开快门不需要这些图像计算依赖。每个 worker 拥有独立样本目录，最多攒 16 帧或 128 MiB 后积分和清理，避免并发删除别人的在途样本；峰值还包括当前一帧样本和积分内存。这个选择性版本没有上游 adaptive `__motion`/位移闸门，多采样有真实成本，先短预览确认。默认快门关闭。

## 验证

`node tests/renderer-stability.cjs` 使用真实浏览器、FFmpeg/ffprobe 和临时项目，检查 PNG/JPEG/CDP 的 scale、profile quality 实际分辨率、4/60 fps、帧数/时长、silent 排除旧配音、浏览器回收后的逐字节确定性、损坏帧修复、输入改动拒绝、渲染期间改动、项目锁、相对 out 与局部快门。可设置 `BROWSER_PATH/FFMPEG_PATH/FFPROBE_PATH/PY`。

原有 `tests/image-ready-render.cjs` 和 `tests/layout-render-validation.cjs` 继续检查图片 readiness 与时间轴错误。完整配音/BGM/工作流回归由项目测试覆盖；本模块测试不调用付费服务、在线 TTS 或读取凭据。
