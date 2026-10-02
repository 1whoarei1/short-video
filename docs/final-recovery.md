# 最终跟踪源码与恢复复验

验收时间：2026-10-01 23:48–23:53 UTC。环境：Linux；Python 3.12.14、Node v24.19.0、系统 FFmpeg 7.1.5、既有 `/tmp/chromium`。

## 结论：本次范围全部通过

目标提交为 `01b7c0a45792f198d17c2238695835f8c6e4ca24`，tree 为 `a76021a19203d2d5c7a02aed0f1acbd32867c2b3`。本说明随后新增，不属于该被测提交。所有运行在独立临时目录完成；没有修改生产源码、推送远端、调用新生图/TTS、读取密钥或使用正式用户项目。

### 干净源码启动和素材

- 用 `git archive 01b7c0a` 解压出独立源码，没有复用主工作区的依赖或运行时项目。
- 在 `vendor/html-explainer/node` 执行 `npm ci --ignore-scripts --registry=https://registry.npmjs.org --offline --cache=/tmp/short-video-npm-cache --no-audit --no-fund`：锁定安装成功，仅安装 1 个包；使用已有官方 registry 缓存，不执行生命周期脚本。
- 独立进程 `python -S -m app.server --port 18809` 的 `/api/health` 返回 `ok: true`、Python `3.12.14`、`bridge: file`、`modelApi: false`。`-S` 禁用 site-packages。本次只验健康接口，没有声称完成网页点击或整条人工审批流程。较早分离进程的端口请求曾被拒绝；在同一测试进程管理服务器、等待就绪并取健康响应后成功，随后正常终止该测试服务器。
- 对 catalog 的全部 **15 个资源包**，逐一实际执行 `python -m app.theme_resources copy ID --workspace 独立临时项目`，均退出 0 并生成复制记录。使用单独新项目，未覆盖任何已编辑副本。
- 干净源码保留 `examples/image-material-study/provenance.json` 和实际 WebP 素材，字节 SHA-256 与 provenance 一致：`decfa5af2b48500585ca375606978750a2f83cc3dbaea13704e8963b5be5eabe`。记录标注原生 AI 生图工具，确切模型未由工具返回；此次不新增模型断言，也未重新生图。

### 最新《山间来信》真实渲染

实际执行：

```sh
BROWSER_PATH=/tmp/chromium MOUNTAIN_LETTER_QA=/tmp/QA node tests/mountain-letter.cjs
BROWSER_PATH=/tmp/chromium python scripts/engine.py render examples/mountain-letter --concurrency 2
ffprobe -v error -show_streams -show_format -of json examples/mountain-letter/out/mountain-letter.mp4
ffmpeg -v error -i examples/mountain-letter/out/mountain-letter.mp4 -f null -
```

- 浏览器测试通过：6 个真实图像素材加载，14 个代表时刻各不相同，反序重访的 14 个截图哈希完全一致；时间钳制、28 秒接口、结尾 arrival/收拢状态通过，页面/请求错误为零。
- 引擎实际截图 **672 帧**，截图阶段约 **36.2 秒**，并完成编码。
- FFprobe：**H.264、1280×720、24 fps、672 帧、28.000 秒、3,339,946 字节**；只有视频流，无音频符合示例配置。
- FFmpeg 全片解码退出 0，无错误输出。实际从 MP4 提取并查看 **3、14、27 秒**：分别为山谷飞信、打开的记忆页、窗边落信；主要文字可读，未见缺图或明显裁切。
- 此次 MP4 SHA-256：`ac8d8d222ab982ae99df3e898c428a0471cc0d4066f83fefe482b5e84fe2cb72`。不同系统/编码器的 MP4 字节不保证相同；这里的哈希用于这次证据文件。

### 基础 + 实际交付增量 bundle 恢复

基础提交：`e6d0504014fd223db060351e7177eccfb71d1da3`。

先实际运行 `git bundle list-heads /tmp/short-video-round7.bundle`，确认公布的是 `refs/heads/overnight-theme-materials`，不是 `HEAD`。随后在全新仓库执行：

```sh
git clone -b main /tmp/clean-checkout-OWL1Wg/base.bundle recovered
git -C recovered bundle verify /tmp/short-video-round7.bundle
git -C recovered fetch /tmp/short-video-round7.bundle refs/heads/overnight-theme-materials:refs/heads/recovered
git -C recovered checkout recovered
```

验证结果：bundle 可用且只要求上述基础提交；恢复后 HEAD 和 tree 精确匹配目标；工作树干净；全部 **500 个跟踪文件**与 `git archive` 解压源逐字节匹配。

- 基础 bundle SHA-256：`5b63d50b0a1feb681482ccb9f44f69fde9f289fb2489a17d037c12059773897e`
- 第七轮交付 bundle SHA-256：`d5bdbec612f533617a22e4df46fcf795e72722bdb276658bbaae5b55b14c5777`

这些校验针对所列既有 bundle；若最终交付加入新的文档提交，需要另行校验最终 bundle 的 HEAD/ref，不可把本次提交标成之后的提交。

## 证据与边界

临时证据根目录：`/tmp/final-source-recovery-wzSsvB`。包含 `health.json`、`npm-ci.log`、`resource-copy.json`、`source-check.json`、`deterministic.log`、`mountain-letter-qa/browser-validation.json`、14 张确定性测试截图、`render.log`、`ffprobe.json`、`decode.log`、3 张实际 MP4 截图、`recovery.log`、`bundle-heads.txt`、`recovered-hashes.txt` 和 `media-bundle-sha256.txt`。实际 MP4 位于该目录的 `source/examples/mountain-letter/out/mountain-letter.mp4`。

这是既有 Linux 环境中从干净源码进行的真实启动、复制、渲染和离线恢复验收，不是全新操作系统安装，也不代表 Windows/macOS 原生验证通过。没有运行新 TTS 或端到端用户审批，未做模型对照实验。临时目录不是可迁移交付件；最终 ZIP 由交付任务单独整理。
