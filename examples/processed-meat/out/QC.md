# 成片质量核验

## 交付口径

- 无声视频，有硬字幕；未生成配音、未发送 TTS 请求
- 12 幕，92.5 秒，1920×1080，24 fps，2220 帧
- H.264 / yuv420p / faststart MP4；只有视频流，无音轨
- HTML + 原创 SVG + GSAP 确定性 seek 逐帧渲染；字幕按作者指定时长显示

## 检查与修正

1. 官方事实与字幕逐项对照，明确证据强度与风险量级的区别。50 g / 18% 所在画面持续保留每日摄入、结直肠癌相对风险和 IARC 2015 限定；没有把 18% 当患癌概率
2. upstream lint_frames.py：12 幕无契约违规；check_beats_refs.py：16 个 B()/Be() 引用全部解析成功
3. 每幕实际代码静态预览已目视检查，确认标题、图形、信息区与字幕安全带不冲突
4. upstream check_layout.mjs 报 46 个 ERROR，原因是其把透明的 1920×1080 SVG 容器当成覆盖全幅的不透明色块。本报告不声称该工具通过；保留原报告用于复核
5. 实际绘制几何检查 check_painted_bounds.cjs：12 幕 × 6 个时间点，共 72 个时间点，0 个可见图形/文字越界或侵入 y>910 的内容。该检查检查 bounds，不代替所有形状之间的遮挡检查
6. 动态抽查发现纸张示意短暂越过顶边。已将平移 SVG 的绝对 y 入场改为相对位移，并同步修正食品/加工图标，整片重新渲染
7. 最终 MP4 解码后逐幕抽帧，包括实际硬字幕和进度条，重新审查12幅。关键开场/纸张/加工图标入场各抽4点核对，不再有上述越界
8. FFmpeg 对最终 MP4 全片解码无错误；ffprobe 计数与声明一致（2220 帧），最终数据见 out/qc/ffprobe.json

## 工程与环境

- 上游 html-explainer 锁定 commit 842c69531fc7ecf4a62265cd83fa8f1ccd4ec677
- playwright-core 1.63.0；实际浏览器为 npm @sparticuz/chromium 153.0.0 的 headless binary
- 系统 full Chromium 的 singleton socket 不可用，官方 Playwright browser ZIP 下载也未成功。使用独立 npm headless 运行时后成功渲染；未改变 OS 安全设置
- 使用本地 Noto CJK 字体与系统 FFmpeg，视频无远程字体、无付费素材
- 初次输出路径错误只影响 mux；后续使用绝对路径，最终成片由修正动画后的全部2220新帧重新编码

## 范围说明

这是公众科普演示，不提供个人医学风险预测。画面中的餐次、分量缩放、相对风险条形图均为解释示意。人工风格的目视审核由本次 agent self-review 完成，不声称真人审核或音频试听。
