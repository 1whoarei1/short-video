# 连续形变与指针交互小样

这是可拆用的原创 6.5 秒无声示范：一个外壳从按钮展开为控制面板，中途修改目标仍保持速度；指针先抵达再触发，拖拽时滑块贴合指针，释放后把速度交给弹簧，最后收回同一外壳。绿色、横屏、界面和长度仅是这次演示的选择。

直接打开 `index.html`，按 Play 播放，或拖动进度条。末尾停止，不冒充无缝循环。`?t=3.4&controls=0` 可定格。没有网络资源、音频、第三方图片或私人成片。

## 按需要拆用

- `motion.js`：纯数值 `spring`、继承速度的 `track`、带端点速度的 `hermite`、局部/屏幕坐标互转。弹簧限定 `omega > 0`、`0 < zeta < 1`，这是此解析实现的数学范围，不是所有作品的动效限制。
- `study.js`：绝对时间状态、目标与交互事件；Node 和浏览器都可读取，输入秒数可任意跳转。
- `scene.js`：Canvas 绘制、同一外壳与裁切、内容错峰、屏幕尺寸指针；原生 `window.__tl.pause(t)/time()/duration()` 接通实际渲染契约。播放计时器只提供秒数，不累计物理状态。
- `frames/01-morph.html`：引擎入口，与独立预览共用源码，播放器控件隐藏。示范使用系统字体，跨机器截图不要求同一个哈希，只比较同次运行的重复采样。

例如可单独取 `spring(elapsed, releaseX, releaseVelocity, target)`，把输出用于 DOM/SVG；每次改目标用旧轨迹在事件点的 x/v 作新起点。不要把样例场景顺序当作新视频必须遵守的模板。创作与检查方法见 [连续运动参考](../../docs/continuous-motion.md)。

## 运行验证与导出

在仓库根目录运行；真实浏览器采用项目锁定的 playwright-core，依赖安装与系统浏览器检查沿用 `scripts/setup.py`，不由例子自动下载软件。

```sh
node tests/continuous-motion.cjs --math-only
# 设置 BROWSER_PATH 为本机已安装的 Chrome/Chromium/Edge 绝对路径
node tests/continuous-motion.cjs
python scripts/engine.py render examples/continuous-motion --concurrency 1
ffprobe -v error -count_frames -show_streams -of json examples/continuous-motion/out/continuous-motion.mp4
ffmpeg -v error -xerror -i examples/continuous-motion/out/continuous-motion.mp4 -f null -
```

`MOTION_RENDER=1 node tests/continuous-motion.cjs`（POSIX shell）还会实际编码并断言 1280×720、30fps、195帧、6.5秒、无音轨和全片严格解码。Windows PowerShell 可先设置 `$env:MOTION_RENDER='1'`。此检查已接入 GitHub Actions。数值检查覆盖改目标的位置/速度连续性、651个几何状态、按下前无变化、拖拽贴合、释放速度和共享镜头变换；浏览器检查15个时间点倒序、6次乱序像素一致及预览/引擎入口一致。

截图和报告默认写入系统临时目录 `continuous-motion-qa`，可用 `CONTINUOUS_MOTION_QA` 指定。输出MP4和缓存不入库。改画幅/fps/时长时同步项目与时间轴；真实配音项目改用本次批准的配音时序。

测试验证可复现行为，不自动证明节奏、美感或阅读舒适度。导出后仍需连续看关键变化及编码代表帧。当前示例没有音轨，不能据此声称听审通过。
