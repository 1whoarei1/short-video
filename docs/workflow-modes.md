# 五阶段制作、运行模式与 Codex 文件桥接

## 用户操作

需求沟通 → 文案（AI 调研并直接写口播稿）→ 静态预览 → 视频制作 → 导出交付。

用户在需求页写 brief、上传资料、选择声音/视觉、给出时长提示，再选模式并确认需求：

- 全流程手动（manual）：每个阶段都交由用户审核
- 半自动（semi）：用户确认需求后，AI 完成调研、文案与真实静态预览；用户确认画面后，AI 制作并检查导出
- 全自动（auto）：用户确认需求后，AI 一直做到检查导出

时长可写约数或最短至最长区间，单位秒。它约束选题和解释密度，不强制引擎卡长度；实际时间由自然讲述、字幕阅读或合成音频决定。

模式不会伪造人工批准。代理审核记录 `approvedBy=agent`、实际检查备注和使用的模式。`selfReview` 仅保留给明确授权的旧测试样片；选择任一正常模式会关闭它。改成更严格模式时，系统重新打开第一个现在需要人工确认、但此前由代理批准的阶段，下游变为需要更新，文件和旧审核证据保留。

## 网页到底会不会自动生成？

网页只读写本机文件，不含模型 API，也不能启动或唤醒已空闲的 Codex 对话。可用的协作链路是：**活跃 Codex 启动 UI → CLI 等待 → 用户网页确认 → CLI 返回请求 → Codex 继续制作**。

```sh
python -m app.server --open
python -m app.cli --workspace workspace wait --timeout 300
```

`wait` 在用户尚未填写需求或尚未批准预览时持续等待，最长 300 秒（可配置 0–3600 秒）。它在收到 queued 请求时返回 `event=request`；取消返回 cancelled，导出完成返回 complete，时间到返回 timeout，退出码 0。超时结果明确说明没有启动生成，用户可回到 Codex 说「继续当前视频项目」。不要把网页的 queued 文案写成「AI 正在生成」。

如果活跃 Codex 正在人工检查点等待，网页确认会自动排队下一段工作。Codex 应再次查看状态并继续到下一确认点；半自动不能在文案处提前收尾，全自动不能在预览处提前收尾。新开/重开对话同样先读 status，而不是覆盖 workspace。

## 代理执行约定

```sh
python -m app.cli --workspace workspace status
python -m app.cli --workspace workspace claim --id REQUEST_ID --revision REV
python -m app.cli --workspace workspace save --stage narration --file script.md --task-id REQUEST_ID --revision NEW_REV
python -m app.cli --workspace workspace submit --stage narration --task-id REQUEST_ID --revision NEW_REV
python -m app.cli --workspace workspace approve --stage narration --by agent --note '实际检查记录' --task-id REQUEST_ID --revision NEW_REV
```

每次成功写入都会增加 revision，下一命令使用最新值。任何长时间渲染或外部执行前后都重读 status，确保请求 ID、mode 和 revision 未变，再决定是否继续或注册结果。已领取任务的代理写入必须携带 task ID。旧任务 ID、过期 revision、取消后的写入都会被拒绝。模式变更会换新请求 ID，阻止旧模式执行者的迟到写入。

`nextAction` 是下一步执行契约：
- actor：human / agent / none
- action：submit_requirements / create / revise / approve / resume / complete
- stage：五阶段之一
- checkpoint：当前模式下下一个必要人工检查阶段，全部可自动时为空
- reason：简明说明

`taskRequest` 包含 ID、queued/running/waiting/cancelled/completed 状态、请求时间、requestedRevision、当前阶段与检查点。`claim` 只领取 queued 项；重复 queued 请求不换 ID；运行中的重复请求被拒绝。人工批准会生成新的继续请求。

每轮：status → 校验 ID → 执行 nextAction → 注册真实产物 → submit → 如果允许代理审核则实测并 approve → 重读后继续。human 检查点提示用户看实际内容，再 `wait --timeout 300`。`wait --after-revision REV` 是可选变化观察，会在任何变化时提前返回 changed，普通等待提交不要传它，避免编辑草稿引起无意义退出。

出错可 `release --id REQUEST_ID --note '具体失败与恢复步骤'`；任务恢复为 queued，不能标记完成。用户暂停用 `cancel --id REQUEST_ID`，只阻止下一次有检查的继续操作，不声称终止已经在运行的 FFmpeg/浏览器进程。已生成文件保留。明确 `request` 才恢复，不能用 release 偷偷解除暂停。

## 状态、回改和迁移

`.studio/workflow.json` schema 2 使用五阶段。旧六阶段项目打开时自动把 research 文字、产物、批注并入 narration；原始 research/narration 字段留在 legacyStages，完整原状态另作内容哈希备份，旧历史快照和真实文件不删除。已批准旧项目只有原 research 与 narration 都已批准，合并阶段才保留批准；其他情况保守重新检查。

`--stage research` 仍是 CLI 的兼容别名，会写入 narration 并记入别名历史；新流程只用 narration。它不是独立审核步骤。旧快照 undo 时也执行无损迁移，不会恢复出隐藏的第六阶段。Undo 恢复状态，不删除文件，也不会复原手动改过的源码。

前置需求、文案、配置、产物修改会把下游设为 stale。必须 revise/重写并重新注册当前版本媒体再提交，不能机械批准旧内容。预览需要真实可读图片；制作和导出需要可验证的视频。代理自动模式没有绕过此检查的特权。

## 自定义主题的便携复用

主题保存于当前项目，内容含名称、说明、创作提示、配色及不可变预览图片。UI 可导出 JSON 主题包，在另一个项目导入；包内嵌图片字节，不能写任意目标路径或覆盖内置主题 ID。导出最多 10 MB，导入最多 8 张、共 7 MB 预览图，校验真实图片结构。主题包可能包含私人素材，只在用户愿意分享时发送给他人。

接口：`POST /api/theme`，`GET /api/themes`，`GET /api/themes/export?id=ID`，`POST /api/theme-import` 的 body 为 `{pack: ...}`。写请求仍检查本机会话 token、Origin、项目和 revision。内置主题/音色资源只从 web/presets 静态加载，声音预览支持 Range 请求，不需要凭据或额外 TTS 调用。
