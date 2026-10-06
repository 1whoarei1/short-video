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

### 2026-10-06：Windows干净克隆实测

独立克隆代码提交`f5c719eadfb822e57ab2fce7c50b4cbd70bf3b0e`，随后快进到仅补充测试的`f181afbcd084813f9d2afbe4ccfce112120ae4ff`；最终测试调整为`093f4af`，生产代码仍与`f5c719e`相同。新建Python虚拟环境，没有复制旧node_modules、Pillow或npm缓存。运行环境为Windows 11 build 26200、Python 3.12.9、Node 22.19.0、Chrome 154.0.8037.98，以及FFmpeg官方入口列出的Gyan便携构建9.0.2。

已完成的真实检查：

- 无第三方Python包的克隆已实际启动UI，健康接口与静态资源可用；另一次无site-packages克隆也在真实Chrome中完成了新项目、保存和重载。浏览器测试工具使用本轮另一个干净克隆新安装的npm运行时，没有借用旧仓库依赖；服务本身不需要这些npm包。
- `setup.py --install`从官方npm registry锁定安装，约4秒；Pillow 12.3.0及numpy 2.5.3从官方PyPI无缓存安装。
- Python回归290项：288项通过，2项Windows符号链接权限测试跳过，耗时105.829秒；上游motion 148项、style 60项通过。
- Windows重复HTTP测试发现未授权响应偶发连接重置，已采用有限响应排空与半关闭修复：20轮假凭据测试共140项通过，新增6项socket回归通过；没有读取或保存真实凭据。
- 实际执行渲染稳定性、因果动效、旧封面及发布封面脚本；生成并完整验证2秒、1080×1920、24fps、48帧的无声演示视频，1600×1200/1200×1600双封面，以及含9项清单文件的ZIP。原图和400px缩略图已查看；本轮未修改视频渲染器。
- 最终共执行19种浏览器脚本，18种通过；本地运行CI列出的10种脚本全部通过，HTTP修复后重复运行的6项核心UI检查通过。全范围主题测试修正测试等待后重新通过；最终再次生成的演示包通过双封面、9项清单哈希及视频完整解码验证。

剩余限制：可选`theme-detail-ui.cjs`在快速打开/关闭序列末尾的零页面错误断言失败，捕获`ThemeMotion is not defined`。其API等待与完整seek序列正常；独立端口的precision-product主题探测中API、时长、动效与页面脚本错误检查正常。失败断言保留，没有把这一项标成通过，也没有因此扩大前端修改范围。

不是全新操作系统安装测试；未新开Codex对话，也未调用真实Azure、Edge或原生生图服务，未做主观听审。上述CI脚本指本地执行结果，远端CI以对应提交的Actions运行记录为准。

[2026-10-06发布验收](publishing-validation-2026-10-06.md)记录了Windows原生Python、Chrome和FFmpeg上的完整回归、实际浏览器、合成视频及双封面发布流程。该记录有明确范围，不能替代之后提交的干净检出复验。

CI与本地验收分别证明其实际执行环境；模拟Windows路径、Linux通过或依赖`ready`都不等于Windows原生已运行。资源许可、生成来源和配音用户选择仍须保留；代理不读取系统凭据，不在验收时导入旧秘密包。
