# 干净检出与 Git bundle 恢复验收

验收时间：2026-10-01。环境：Linux。目标提交：`639e977d58d2278923d15f54dc64d4e56ab6338d`。

## 结论：通过

已实际完成：仅跟踪源码启动、新项目与首次需求保存、内置资源加载、已有原生生图素材登记、浏览器代表帧、12 秒真实视频渲染，以及基础提交加增量 bundle 的恢复。未写入 GitHub，未修改正式工作区。

## 实测证据

- 将 `git archive HEAD` 解压到独立临时目录，共 **487 个普通文件**。归档中没有 `node_modules`、用户 workspace 历史、`.studio`、npm 缓存或真实 `.env` 路径。`tts.env.example` 与凭据处理源码/测试属于预期文件。这里只检查归档路径，**不等同于完整密钥扫描**。
- 在解压目录执行 `python -S -m app.server --port 18795`；`-S` 禁用 Python site-packages 加载。健康接口返回 `ok: true`、Python `3.12.14`、文件桥接、`modelApi: false`。依赖报告指出缺少 `playwright-core`，但 UI 正常启动。
- 确认默认需求为空，通过 UI 使用的带令牌本地 HTTP API 创建新项目，再确认新项目为空，按当前 revision 保存首次需求。新项目路径位于独立解压目录，没有继承旧私人项目。仓库自带公开示例仍按设计显示。
- **15 个主题包目录、23 个 WOFF2 字体、5 个预录音色 MP3** 均成功读取；字体和音频响应逐字节匹配仓库文件。这证明资源可加载，不代表实时配音或所有字体视觉度量已验证。
- 随后用 Chromium 以 1440 × 1000 打开工作台：新项目可见，页面脚本错误为零。前述创建/保存是实际 HTTP 操作，不能表述成点击按钮完成。
- 执行锁定安装：`npm ci --ignore-scripts --registry=https://registry.npmjs.org --offline --cache=/tmp/short-video-npm-cache --no-audit --no-fund`。从已有官方 registry 缓存安装唯一依赖 `playwright-core`，未运行生命周期脚本或额外下载。
- 使用 `app.theme_resources` 复制 `prismatic-lab`，得到 **21 个文件**及复制收据，包含依赖和来源记录。用 `app.image_assets` 登记已有 `prism.webp`：129,574 字节，解码验证后不可变快照 SHA-256 为 `decfa5af2b48500585ca375606978750a2f83cc3dbaea13704e8963b5be5eabe`。原记录注明使用原生 AI 生图工具，但工具未返回确切模型，本次不作模型断言，也没有重新生图。
- 仅改编独立副本，使用可选 `engine-bridge.js` 接入单场景。建立 12 秒无声时间轴，实际渲染并查看第 6 秒代表帧，再通过 `/tmp/chromium` 执行完整渲染。
- FFprobe 验证：**H.264、1280 × 720、24 fps、288 帧、12.000 秒、1,811,598 字节**。FFmpeg 全片解码无错误。无声音轨符合测试设置；没有调用 TTS、音乐服务、模型 API、密钥或支付。

## bundle 恢复：通过

基础提交：`e6d0504014fd223db060351e7177eccfb71d1da3`。

目标提交：`639e977d58d2278923d15f54dc64d4e56ab6338d`。

在独立仓库中，从基础 bundle 加载基础历史，验证并导入增量 bundle，检出目标提交。恢复后工作树干净，提交完全一致，tree 为 `d457cea23e850fcc92273d44e0d5eb6c0aa4ad73`；全部 **487 个跟踪文件**与源码归档逐字节一致，全程只使用本地 bundle。

**先查看 bundle 实际公布的 ref，不要猜名称：**

```sh
git bundle list-heads /absolute/path/increment.bundle
git -C recovered bundle verify /absolute/path/increment.bundle
```

本次临时测试用 `git bundle create increment.bundle main..HEAD` 创建，公布的 ref 是 **`HEAD`**，所以实际成功命令为：

```sh
git -C recovered fetch /absolute/path/increment.bundle HEAD:refs/heads/recovered
git -C recovered checkout recovered
```

交付 bundle 公布的是 **`refs/heads/overnight-theme-materials`**，与该临时测试不同。先核对 `list-heads` 输出，再使用对应命令：

```sh
git -C recovered fetch /absolute/path/increment.bundle refs/heads/overnight-theme-materials:refs/heads/recovered
git -C recovered checkout recovered
```

增量 bundle 需要基础提交已存在。基础 bundle 若没有默认 HEAD，可用 `git clone -b main /absolute/path/base.bundle recovered` 明确选择基础分支。本次初次误用分支 ref 读取仅公布 `HEAD` 的临时增量包，安全失败；改为实际公布的 ref 后恢复成功。

## 验收范围

这是 Linux 上真实执行的 CLI、HTTP、浏览器和渲染验收，使用系统已安装的 Python、Node、FFmpeg、Chromium；不是全新操作系统安装测试，也不代表 Windows/macOS 原生验收通过。

**没有实际新建 Codex 对话并发送“我要制作视频了”。** 当前测试会话人工遵循仓库启动说明，执行了上述真实运行步骤。需求仅保存，未冒充用户提交或人工批准；视频属于独立引擎验收产物，不能声称已完成完整用户工作流。

临时证据保存在 `/tmp/clean-checkout-OWL1Wg`，包括 setup、HTTP、UI、图片登记、渲染、恢复日志，截图、bundle 和独立视频。临时文件不是可迁移交付件，也未加入 Git。本验收任务只在主检出目录新增本说明文档。
