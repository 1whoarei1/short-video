# 个人自定义主题：短动态预览

自定义主题仍是自由创作参考，不是强制模板。旧图片主题和 schemaVersion 1 图片主题包保持兼容；不改变五阶段、三种模式、旁白、人物、音色、语速或需求分组。

## 使用

1. 在需求页导入个人 MP4 / WebM 参考视频（现有项目上传入口），或由 Codex 注册项目视频产物。
2. 功能设置 → 创建自定义主题，填写名称、视觉方向，可选图片和一个短动态预览。
3. 保存后在主题选择器预览：小卡片静音循环播放（尊重减少动态效果偏好）；“放大播放与查看素材”打开原生视频播放、暂停、拖动进度条和全屏控件。
4. 查看预览不会选择主题。点击“使用这个视觉方向”后才修改选择，保存需求后生效。
5. 导出 JSON 主题包包含方向、配色、来源主题 ID、图片及可选视频。可在其他项目导入。个人素材保存在当前项目，没有上传服务，也不会自动 Git push。导出的文件包含个人媒体，请自行保管。

无需新增专用上传接口。原有参考视频上传最多 8 MB，但作为主题动态预览须通过以下更严格限制；上传参考资料成功不代表动态预览验证通过。

## 安全与数据格式

- 可选主题字段 `animation` 在工作流状态中保存 `{path, sha256, duration, width, height}`。保存时读取一次原始字节，完整验证，再按 SHA-256 保存不可变项目快照；不再引用可修改的来源文件。
- 可移植 JSON 在顶层添加 `animation: {extension, data}`。extension 仅 `.mp4` / `.webm`，data 是严格 base64。拒绝额外动画字段与导入路径；尺寸、时长和哈希来自本地验证，不信任主题包里的声明。
- 单视频最多 6,000,000 字节、15 秒、1920×1920、60 fps、900 解码帧。主题包图片与动画合计最多 7,000,000 解码字节；创建、导出和导入共用此限制，拒绝保存不能自行往返的超限组合。导出的 JSON 最多 10 MB。
- 为保证浏览器原生播放，MP4 视频仅接受 H.264 / 8-bit 4:2:0（yuv420p 或 full-range yuvj420p），音频仅 AAC；WebM 视频仅 VP8/VP9 / 8-bit yuv420p，音频仅 Opus/Vorbis。编码不兼容时提示重新导出，不改写原始素材。
- 必须有本机 FFmpeg / ffprobe。缺失时返回明确依赖错误，不以容器签名代替解码验证，不自动安装。
- 强制 MOV 或 Matroska 解复用器，输入为内存字节的 stdin pipe，仅允许 `pipe` 协议。禁止网络、外部本地文件引用和播放列表；不会执行导入的 HTML / SVG / 脚本。视频及可选音频均完整解码；探测和完整解码均限时、单线程、限制解码器像素数及单次分配 64 MB（不是全进程内存上限）；解码错误、超时、伪装音频或无有效帧均拒绝。
- MP4 须自包含且适合流式读取。不能完整通过 pipe 解码的文件应重新导出为 faststart MP4，或使用 WebM；不会为兼容性开启文件/网络协议。
- 项目媒体沿用 `/assets/` 的 Range、nosniff 和 `sandbox; default-src 'none'` 防护，不放宽 CSP。内置可信 HTML 动画保留原有隔离逻辑；自定义主题仅用原生 video。
- 保存/导入沿用项目 revision 乐观锁、操作期间控件锁定、错误反馈和未保存表单提醒。验证失败不写入主题状态，导入临时文件在失败/成功后均清理。

## 验证

- `python -m unittest discover -s tests -p test_custom_theme_animation.py -v`：实际 MP4/WebM 编解码与可移植往返、旧格式、源文件修改后快照、假容器/截断/播放列表/HTML、音频伪装、尺寸/帧率/时长限制、依赖缺失、路径注入、过期 revision、聚合大小越界/恰好 7 MB 往返、MPEG-4 Part 2 拒绝及探测器参数限制。
- `node tests/custom-theme-animation-ui.cjs`（`BROWSER_PATH=/tmp/chromium` 默认）：实际上传/保存/导出/导入、原生播放/暂停/seek、未确认不选择、移动端无横溢、桌面、媒体 Range/CSP/nosniff、无页面脚本错误。
- `node tests/full-range-theme-ui.cjs`：实际 full-range H.264/yuvj420p MP4 上传、保存、导出/导入、浏览器播放、等待 seek 完成；可用 `THEME_VIDEO_FIXTURE=/path/to/rendered.mp4` 验证渲染器产物。WebM 仍只接受 yuv420p，10-bit 和 4:4:4 不在支持范围。
- 既有 `test_creation_upgrade_review.py`、`test_studio_http.py`、`test_workflow.py` 和 `theme-detail-ui.cjs` 回归通过。
- 实测环境为 Linux；Windows/macOS 原生未实测。浏览器原生支持的具体视频编解码器可能因系统而异。
