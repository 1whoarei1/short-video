# 导出视频与发布包

发布材料属于最后的导出阶段：一个视频标题、一段简介、一组话题，以及横版 **4:3** 和竖版 **3:4** 两张真实封面。封面比例与视频画幅无关，不用16:9或9:16代替。文案可编辑、保存、分项或全部复制；两张封面可分别预览、放大、下载和替换，明确请求后重新生成。

`auto` 由活跃Codex在导出前主动完成文案、双封面及核验，不新增人工gate。`manual/semi` 保留原有导出审核语义。网页只持久化请求，不能启动模型或唤醒空闲Codex；请求排队时回到当前Codex对话说「继续当前项目的发布材料」。未实际取得并验证文件时，状态不能当作生成完成。

## 内容与编辑保护

Codex先读本项目已确认需求、口播、来源与实际成片，围绕用户指定重点写文案，保留语气和事实范围。标题应兑现片中内容；简介补充必要背景，话题与实际内容有关。不套固定营销标题、不夸大风险，不自动向第三方平台发布。

普通保存不会调用TTS、重建时间轴或重新渲染视频。已有用户编辑不被普通自动生成覆盖；明确重新生成仅授权请求中的目标。保存文字或替换封面会取消进行中的旧发布请求，迟到结果被拒绝。视频内容、对应素材或配置变化时，原文案及封面保留并提示可能过期；改一项不能让其他旧材料自动变成有效。代理须重新核对全部相关材料，选择明确重新生成，或经实际检查登记保留现有材料的理由。

状态保存在项目 `.studio/workflow.json` 的 `publishing` 字段；仍只通过CLI/UI写入。新项目启用完整发布包。没有该字段的旧项目保留原导出行为；使用发布功能后启用本项目发布检查，不自动改写旧文案、旧封面或旧视频。

## 任务领取与真实生成

先用 `python -m app.cli status` 取得网页当前项目的绝对 `workspace`，随后固定该路径。发布请求与视频任务分别使用ID，不把视频 `taskRequest.id` 当作发布ID；网页切项目也不改变已经领取的目标。

```sh
python -m app.cli --workspace PROJECT status
python -m app.cli --workspace PROJECT publishing request --by agent --targets text landscape portrait --revision REV
python -m app.cli --workspace PROJECT publishing claim --id PUBLISH_ID --revision NEXT_REV
```

从返回的 `publishing.request.id` 取发布ID。请求状态为 `queued → running → completed`，取消为 `cancelled`。相同目标、内容和方向的重复请求不创建第二个任务；已有任务未取消时不能改成另一个生成请求。每次成功写入后使用最新的**项目revision**，不要把 `publishing.revision` 的编辑计数拿来代替。长时间工具调用前后重读status：内容指纹变化、用户编辑、取消或请求替换后，旧执行者停止登记。

`status` 的 `publishing.enabled/ready/stale` 分别表示本项目是否启用、材料是否实际齐备有效、是否存在过期材料；`covers.landscape/portrait` 保存两张验证记录，`request.id/status` 保存当前生成请求。需要指定重做方向时，在 `request` 上加 `--direction '本次修改要求'`；只重做一张可用 `--targets portrait` 或 `--targets landscape`，只重做文案用 `--targets text`。首次完整包仍须三项齐备才可完成。

自动代理发起请求时使用 `--by agent`，只选择缺失或可更新的目标；`textUserEdited` 或封面 `userEdited` 已标记的项不会被这种请求覆盖。明确的用户重新生成请求（UI或已授权的 `--by human`）才允许重做相应手改项，代理不能把自己的普通续作冒记为用户请求。用户改过的材料遇到视频变化时，保留并实际核对，必要时用下文 `review-current` 记录仍适用的理由，不能自动改写。

代理必须真正写文案、调用本会话实际可用的生图工具，或编写并渲染HTML/CSS封面。项目没有内置模型API，不需要新增密钥、付费服务或第三方发布账号。工具不存在就说明阻塞并继续可行路线，不用提示词或空文件假装已完成。

文案输入是项目内UTF-8 JSON，例如 `publish/text.json`：

```json
{
  "title": "比较增长，先看基期",
  "description": "同样的增长比例，放在不同基期上，代表的实际变化也不同。本片用两组数字说明比较时需要一起看的量。",
  "topics": ["数据解读", "增长率", "基期"]
}
```

示例只是通用演示内容，不是其他项目的固定文案。话题保存为字符串数组，输入可以带 `#`，输出统一排成标签。`--file` 从当前命令目录读取，下面用 `PROJECT/publish/text.json` 表示该项目文件的完整路径；Windows含空格路径应加引号。封面的 `--path` 则必须是项目内相对路径。

```sh
# 代理按已领取的发布请求登记真实文案
python -m app.cli --workspace PROJECT publishing text --id PUBLISH_ID --file PROJECT/publish/text.json --revision REV

# 用户主动编辑保存；会保护新版本并取消旧生成请求
python -m app.cli --workspace PROJECT publishing save --file PROJECT/publish/text.json --revision REV
```

## 双封面的两条路线

两张封面分别安排标题、主体和留白，沿用本片的字体、核心palette与视觉语言。推荐1600×1200和1200×1600；实际完整解码后必须为精确4:3或3:4，短边至少300像素。不是机械裁同一图，也不强制套版。

### 当前会话的原生生图

读取 [图片素材技能](../.agents/skills/video-image-assets/SKILL.md)，确认工具实际存在；检查授权参考、调用工具、按工具原生流程取得项目内真实文件，再查看像素。记录实际提示词、来源、授权参考和工具确实报告的模型名，未知模型名留空。需要精确排字时可生成主体后另用代码排版，分别保留生成和合成来源。`image_mode=existing` 不登记AI生成素材，可使用授权已有素材或代码图形。

发布封面登记会完整解码、校验尺寸，生成内容哈希快照，并写入图片素材记录。发布任务使用独立ID，直接走下列发布接口；不要把发布ID传给仅检查视频任务的 `app.image_assets --task-id`。

```sh
python -m app.cli --workspace PROJECT publishing cover --id PUBLISH_ID --by agent --orientation landscape --path publishing/incoming/generated-landscape.png --source ai-generated --prompt '本次实际提示词' --note '已看原图和手机小图，核对主体、标题及裁切' --revision REV
python -m app.cli --workspace PROJECT publishing cover --id PUBLISH_ID --by agent --orientation portrait --path publishing/incoming/generated-portrait.png --source ai-generated --prompt '本次实际提示词' --note '竖版独立构图，已核对标题可读性及边缘' --revision NEXT_REV
```

`--model` 仅填实际报告的名称；`--origin` 保存授权来源或项目内来源说明。来源是作者声明，不是模型服务商的签名证明。

专用封面输入建议放在 `publishing/incoming/`，HTML渲染输入放在下文的 `publish/`，与视频的 `assets/` 分开；普通视频素材仍是内容依赖，不能把发布用临时文件塞进去后忽略其变化。

### 自由HTML/CSS与真实浏览器截图

由代理独立创作 `publish/cover-landscape.html` 与 `publish/cover-portrait.html`，画布分别1600×1200、1200×1600。可以自由使用HTML/CSS/SVG/Canvas和授权本地素材，不要求固定元素布局。标题用可见的 `h1`、`.hook` 或 `[data-cover-hook]` 标记，供检查器识别，其他结构自由。

```sh
node scripts/render_publish_covers.mjs PROJECT --only all
# 只重做一种比例；可明确指定已安装的官方浏览器
node scripts/render_publish_covers.mjs PROJECT --only portrait --browser /path/to/Chrome --scale 1
```

`--only` 可选 `all|landscape|portrait`，`--scale` 为1或2。默认输出上述尺寸PNG；2倍输出3200×2400、2400×3200，比例不变。实际输出为 `publish/cover-landscape.png`、`publish/cover-portrait.png` 和 `publish/cover-render-report.json`。该路线记录为 `html-css-chromium` / `code-generated`，不冒充imagegen。

渲染器等待字体、图片与可选 `window.__assetsReady`；有 `window.__tl` 时取最终状态，静态HTML也可用。全部请求的封面验证成功后才替换相应输出。资源必须在项目内；拒绝外部请求、项目外文件、缺失图片及运行错误。检查实际解码尺寸、文字溢出/裁切/重叠、标题4%安全边距，以及400像素小图上的标题字号。检查成功仍须实际看原图和小图，确认主体、对比度和手机可读性，不能把技术通过当作审美通过。

```sh
python -m app.cli --workspace PROJECT publishing cover --id PUBLISH_ID --by agent --orientation landscape --path publish/cover-landscape.png --source code-generated --origin publish/cover-landscape.html --note '独立横版HTML；已看原图和手机小图' --revision REV
python -m app.cli --workspace PROJECT publishing cover --id PUBLISH_ID --by agent --orientation portrait --path publish/cover-portrait.png --source code-generated --origin publish/cover-portrait.html --note '独立竖版HTML；已核对裁切与标题' --revision NEXT_REV
```

旧 `python scripts/engine.py cover PROJECT` 仍保留，既有比例和生成器不受影响；其16:9/9:16等输出不能自动替代本次发布包要求。

## 完成、取消与保留现有材料

```sh
python -m app.cli --workspace PROJECT publishing complete --id PUBLISH_ID --note '已对照确认稿；实际核对两张封面的比例、原图及小图可读性' --revision REV
python -m app.cli --workspace PROJECT publishing cancel --id PUBLISH_ID --revision REV
```

`complete` 要求本次请求的每个目标都有真实保存登记（`doneTargets`），并且当前内容有效的标题、简介、话题与两张实际封面齐备，随后生成交付文件；空文案、缺封面、错比例、快照损坏或过期材料会失败。取消阻止后续登记，不声称已杀掉外部工具进程；代理不能看到取消后就自动发新请求解除暂停，明确恢复后再领取。替换封面不传 `--by agent` 时按用户替换处理，保留新版本并取消旧请求。

视频变化后若材料仍正确，先实际对照成片和全部现有材料，再登记：

```sh
python -m app.cli --workspace PROJECT publishing review-current --note '说明逐项检查后仍适用的事实与视觉依据' --revision REV
python -m app.cli --workspace PROJECT publishing export --revision NEXT_REV
```

`review-current` 不生成内容，不能拿来掩盖未检查或不存在的文件。仅修改发布文案、替换封面后，可用 `export` 重建包，不重新执行视频制作。正常新视频流程仍注册并检查视频、字幕与音轨，随后按原模式提交/批准export；发布包不能代替视频媒体验证。

## 下载、项目包与来源

交付输出在项目 `publishing/delivery/`：

| 文件 | 内容 |
| --- | --- |
| `publish.txt` | 可读的标题、简介和 `#话题` |
| `publish.json` | 文案、双封面记录、来源声明和内容指纹 |
| `manifest.json` | 包内文件的路径、字节数与SHA-256 |
| `publishing-package.zip` | 上述文字与清单、两张封面，以及当前production/export版本已登记的交付文件 |

封面登记保存于 `publishing/covers/` 的不可变哈希文件；UI预览和下载使用这些实际文件。只打包当前版本的已登记交付文件，不扫描整个私人项目目录。需要复现时，代理先把必要场景源码、封面HTML/素材来源、渲染报告及许可说明作为源文件或源包登记到导出阶段，再构建最终发布包；未登记的任意源目录不会自动进入ZIP。不要把凭据、私人无关资料、缓存或历史状态混进源码包。

保存、替换或内容变化后须重新导出当前发布包。下载接口校验当前指纹、版本和文件哈希，缺失或改变的包不会当作当前交付。私人图片和此前视频保留在用户项目内，公共仓库验收使用 [通用演示项目](../examples/publishing-package-demo/README.md)，不自动修改此前已交付的加工肉封面。
