# Codex：视频制作项目入口

用户说「我要制作视频了」或类似意图时，主动完成下面流程，而不是只解释仓库。

1. 读取 `.agents/skills/video-workflow/SKILL.md`；写稿前读取 `.agents/skills/video-narration/SKILL.md`。
2. 确认当前目录和操作系统。运行 `python scripts/setup.py`（Windows 可用 `py -3`）。缺少 Python 时给出官方安装指引。UI 本身仅需 Python 3.10+，无需先装渲染依赖。
3. 启动 `python -m app.server --open`，保持服务进程运行，检查 `http://127.0.0.1:8765/api/health`，告诉用户打开本机地址。端口占用时先检查是否已有本项目服务；否则使用 `--port 8766`。不要关闭无关进程。
4. 读取 `python -m app.cli status`；新项目从需求沟通开始。问最有用的少量问题：主题、受众、时长/画幅、观众看完要理解什么。用户已有足够信息就先组织需求草案。
5. UI 不调用模型，也不会通过保存按钮自动开始生成。你是执行者：读取项目状态与批注，调研、写文件、执行检查，注册产物，然后提醒用户在 UI 审核。

## 重要边界
- 正常项目逐阶段需要用户确认。仅用户明确授权的测试或样片可运行 `mode --self-review on`。自审必须记录实测结果，不能伪造用户批准。
- 默认制作无声、带字幕视频；用户可在需求配置选择 Microsoft Edge 或 Azure Speech 配音。Edge 配音遵循 `docs/edge-tts.md`，Azure 配音遵循 `docs/azure-tts.md`，由用户在本机安全配置认证，禁止把密钥放入聊天、项目文件、网页表单、日志或 Git。文案批准后再合成，以真实音频与词边界生成字幕和场景时间；语音或文案改变后重新核对下游。
- 允许自由 HTML/CSS/JS 视觉创作。不要引入强制组件库、固定元素 ID 或套版结构。渲染器所需的场景接口见 upstream 文档；这与视觉组件无关。
- 原创方向默认可用，主题系列包是可选的创作参考；不要加入每字段“参考/强制”开关。
- 工作流状态在 `workspace/.studio/workflow.json`。引擎配置在 `workspace/project.json`，两者不可混用。
- 回改前置阶段必须让下游进入 stale 并重新核对。不要只修改导出成片掩盖过期脚本。文件与批注分别保留。
- 用户未授权安装或外部执行时，先检查环境并说明必要依赖；不修改其安全设置。使用官方 Python、Node、FFmpeg 和 Chrome/Chromium/Edge。
- 不提交密钥、私密素材、node_modules、用户 workspace 历史或临时缓存。发布前确认文件范围。
