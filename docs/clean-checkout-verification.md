# 干净检出验收

新机器使用方法见[新机器设置](new-machine-setup.md)。本页说明怎样证明仓库能独立运行，避免将路径发现、旧缓存或历史报告当作当前版本的执行结果。旧bundle恢复和临时目录报告保留在Git历史，不再作为首次启动入口。

## 验收步骤

在独立克隆中测试，不使用正式用户workspace、密钥或私人素材：

1. 记录实际提交SHA、Windows/macOS/Linux版本、Python/Node/FFmpeg与浏览器版本；检查跟踪文件没有运行时依赖或用户项目。
2. 尚未安装可选Python包时启动UI，检查`/api/health`，创建空白项目并保存需求。仅有渲染依赖缺失不应阻止UI启动。
3. 从官方来源准备渲染依赖，执行锁定npm安装；需要完整图片和声音测试时，在同一Python环境从官方PyPI安装Pillow及测试使用的numpy。记录安装来源和结果。
4. 运行Python回归及实际浏览器检查；用临时项目测试编辑、重载、切项目、批注和发布任务，保留失败、跳过及限制说明。
5. 用通用示例实际取帧和渲染，完整解码视频，核对分辨率、fps、帧数、时长与音轨；不能只看渲染报告。
6. 解码并查看4:3/3:4封面及400px缩略图；生成真实TXT/JSON/ZIP，解压核对清单哈希、图片和登记的源文件。
7. 说明是否实际新开Codex对话、调用在线配音/原生生图、试听声音或安装全新操作系统；未做的项目不写成通过。

PowerShell基础命令：

```powershell
py -3 scripts/setup.py --json
py -3 -m app.server --port 18795
# 在另一终端检查该端口健康状态
Invoke-RestMethod http://127.0.0.1:18795/api/health
```

安装获准后：

```powershell
py -3 scripts/setup.py --install
py -3 -m pip install --index-url https://pypi.org/simple Pillow numpy
py -3 -m unittest discover -s tests -v
$env:BROWSER_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
node tests/ui-smoke.cjs
node tests/publishing-ui-smoke.cjs
node tests/publishing-cover-smoke.cjs
```

`numpy`用于部分测试与音乐信号处理，不是打开UI的依赖。浏览器路径替换为实际安装值；测试前设好FFmpeg/ffprobe所在PATH。在线服务不会因安装包或离线测试通过而自动获得授权。

## 已有验证与限制

[2026-10-06发布验收](publishing-validation-2026-10-06.md)记录了Windows原生Python、Chrome和FFmpeg上的完整回归、实际浏览器、合成视频及双封面发布流程。该记录有明确范围，不能替代之后提交的干净检出复验。

CI与本地验收分别证明其实际执行环境；模拟Windows路径、Linux通过或依赖`ready`都不等于Windows原生已运行。资源许可、生成来源和配音用户选择仍须保留；代理不读取系统凭据，不在验收时导入旧秘密包。
