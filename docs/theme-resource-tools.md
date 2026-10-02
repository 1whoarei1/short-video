# 让 Codex 快速找到并使用资源

1. 搜索：`python -m app.theme_resources list --query "产品 玻璃"`。按名称、标签、说明匹配，只返回相关包，避免把全部源码塞进上下文。
2. 了解：`python -m app.theme_resources show precision-product`。读取用途、预览入口、素材、共享代码和改编建议。
3. 看效果：在工作台主题列表点“放大播放与查看素材”，手机也能播放、暂停和拖动；未确认前不会改选主题。
4. 复制：`python -m app.theme_resources copy precision-product --workspace PROJECT`。资源进入 `assets/theme-resources`，原相对目录保留，共享材料可被多包复用。不会改动当前主题、人物、音色或语速。
5. 根据本次内容重写构图、运动与镜头。可以只用一张图或一个方法，也可融合多个包；副本允许自由编辑。

领取工作流任务后 copy 需带 `--task-id ID --revision REV`。每次写入前核对状态。若目标文件已有人工/AI修改，命令拒绝覆盖；使用 `--destination assets/theme-resources-v2` 获取独立新副本。不会静默覆盖或删除。

复制后输出实际 preview、manifest、receipt 路径。清单包含文件哈希，便于核对来源；共享资源放在同一目录。资源复用只是创作起点，事实、配音和实际视频时长仍按当前项目要求处理。

跨包借用的素材按清单自动复制，并保留来源目录。例如 cinematic-inquiry 可使用 tactile-archive 的图像，同时继续使用共同的叙事动效代码。
