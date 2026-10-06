---
name: video-image-assets
description: 按内容关系为 HTML 视频规划、生成、验证和复用图片素材，与图形代码保持全片连续设计语言；使用当前 Codex 原生生图工具，不配置模型 API。
---
# 视频图片素材

1. 读取当前 workspace 状态、需求、themeId、image_mode、image_direction，以及已选人物、旁白、音色和语速。保留用户选择。每次操作检查请求 ID、revision 和取消状态。
2. 先逐句或逐段判断要表达的关系、变化、比较或因果，再从主题包/shared挑少量材料，按需生图表现质感、环境、物件或插画。图片与图形代码自由组合，保持HTML/CSS/JS主底层；准确文字、图表数据、证据与科学结构由可核验代码或真实来源承担。资源示例是材料，不是固定模板。
3. 先识别当前会话实际提供的生图工具和适用技能。用户报告 GPT-6-Luna 支持 image2.5，但不要凭模型名假定工具存在。image_mode=existing 时跳过生图。工具不可用时如实记录，使用已有授权素材或代码图形继续能完成的部分。
4. 在项目内编写 assets/image-plan.json，数组每项包含 id、purpose、prompt，可选 aspect、transparency、consistency、references（这些字段都是字符串）。运行 `python -m app.image_assets --workspace PROJECT plan --file assets/image-plan.json`。此计划是素材需求，不规定场景结构。
5. 按本次用途调用真实生图工具。参考图片先检查像素；人物/产品一致性可复用授权参考。透明底需求在工具中明确。不得把整段旁白截图当画面。遵循工具原生文件保存/传输流程，取得真实本地文件后才说生成完成；勿把显示图片或想象的路径冒充已落盘素材。
6. 将图片保存到项目内，如 assets/incoming/object.png。运行 `python -m app.image_assets --workspace PROJECT record --file assets/incoming/object.png --purpose '主体物件' --source ai-generated --model '实际工具报告的模型' --prompt '实际提示词'`。来源是作者声明，字节验证不证明生成模型；不要填写未经确认的模型名。code-generated/user-supplied/licensed-reference 用于其他来源。
7. 领取任务后的上述命令必须在子命令前附 `--task-id ID --revision REV`。返回不可变快照路径后按 stageOrder 用现有 `app.cli artifact --stage preview` 注册；全自动改用 `--stage production`，带相同任务检查；查看实际图片，检查手指/文字/物件外形/透明边缘、裁切和缩放，失败就修改或重做。
8. 把真实图片放进 HTML/CSS/SVG/Canvas 场景并渲染代表帧。手动/半自动将素材审核与静态预览合并；全自动在视频制作内核对素材并直接渲染成片，不创建静态预览阶段或新增人工审核。保存生成来源和提示词可供以后复用，私人素材与生成历史留在项目内，不提交到公共内置主题库。

素材可以自由跨主题组合，必要时生成补充图。复杂场景应先证明最难的几秒动效，再扩大制作。生图能力是当前会话提供的，项目不会通过 UI 自动启动模型。

生成前和编码抽帧后对照全片的字体、核心palette、材质与标识；同一主体跨镜头保持身份和设计语言。写实图片与扁平代码图形混用时协调底色、光线、描边和纹理，不直接拼成两种风格。有意明暗变化可以保留，不把同一底色或暗色食品视觉固定为全部视频要求。镜头内要有解释关系的变化，静态图片与文字入场不能承担全部动画。详见 [创作与验收参考](../../../docs/creative-method.md) 与 [视觉材料工作法](../../../docs/visual-remix-guide.md)。

登记图片前检查 Pillow 是否可用；缺少时按当前环境的安装授权处理，不能跳过解码。核心 UI 不要求此依赖。
