# 在 Codex 里为视频生成素材

需求页“图片素材创作”可选择允许按需生图或只使用已有素材/代码图形，并补充图片方向。你仍然选择人物、旁白音色与语速。

当前 Codex 读取 `.agents/skills/video-image-assets/SKILL.md`，调用自己实际可用的生图能力，保存图片到项目，再加入场景。UI 不接收 API 密钥、不硬编码模型名称、不伪造后台生图任务。工具不可用会明确记录，继续使用现有素材。

使用 `python -m app.image_assets --workspace PROJECT list` 查看计划和真实素材记录。plan 接收项目内 JSON 计划；record 验证 PNG/JPEG/WebP 并保存哈希快照，记录用途、提示词和来源。领取视频任务后传 `--task-id` 与 `--revision`。真正加入预览审核仍使用现有 app.cli artifact 命令。

记录中的模型名与来源由作者声明，不是服务商签名证明。请检查图片是否适合实际内容；生成插画不能充当新闻照片或事实依据。代码负责准确排字，来源数据负责图表与数字。

图片登记需要 Pillow 完整解码器（python -m pip install Pillow）；未安装时明确拒绝登记，不以文件头检查冒充完整验证。UI、素材计划和列表仍不依赖 Pillow。登记在实际解码之后重新核对任务，并与取消/修改共用工作流写锁。
