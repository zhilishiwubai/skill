# Scientific figure optimizer 0.1.3

将 CSV 科研曲线及任务单转换为可复现、可编辑的数据图。Agent 负责理解修改请求、建立任务单、解释诊断及组织人工核查，Python 程序负责保真绘图与确定性检查。

## 安装

使用已安装的 Python 3.12。先确认 `python --version`，再建立独立环境，在本模块目录运行。锁定依赖针对 Python 3.12。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe scripts/install_skill.py
```

安装器复制 SKILL.md、scripts、references、assets 到实际 CODEX_HOME 下的 skills/scientific-figure-optimizer。CODEX_HOME 未设置时使用用户目录中的 .codex。已存在的目标会报错，避免覆盖。重新打开会话以发现 skill。程序依赖安装在虚拟环境中，调用时选用该环境的 Python。

安装器也复制 requirements-lock.txt 和 LICENSE。更新已有 skill 时，先将旧 skill 完整备份至其他目录，再用安装器安装到腾出的路径；不覆盖混合版本。仅依靠安装资源运行的模板是 `<skill目录>/assets/brief-template.json`，配套 CSV 也在 assets 中。

## 完整教学案例

公开 CSV 是本项目自行编写的确定性教学数据，分别演示弹性关系和衰减振动。它们没有实验或模型验证含义，按 CC0-1.0 提供。曲线全部保留输入点序。

```powershell
.venv\Scripts\python.exe scripts/figure.py check examples/spring.json
.venv\Scripts\python.exe scripts/figure.py render examples/spring.json --out runs/spring-v3
.venv\Scripts\python.exe scripts/figure.py verify runs/spring-v3
.venv\Scripts\python.exe scripts/figure.py render examples/decay.json --out runs/decay-v3
.venv\Scripts\python.exe scripts/figure.py verify runs/decay-v3
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

查看 figure.png、final-size.png 和 grayscale.png。记录读者问题、数据来源和必须保留的信息，核查数值、显示范围、最终尺寸和科学表达，再批准使用。输出目录里的 REPRODUCE.md 说明如何独立重跑。更多步骤见 [教程](docs/TUTORIAL.md)。

每次使用新的输出目录；已存在目录会拒绝。`check` 负责任务单和数值校验；`render` 才检验字体、字形、对比、布局与导出。失败返回状态码 2，render 的临时目录被清理。`verify` 重新读取文件，失败时将本目录 verification.json 标记 FAIL；此操作用于避免旧 PASS 误导。核查会校验必需文件、哈希、SVG顶点/裁剪区/参考位置、PDF字体与页面、PNG像素和DPI。

0.1.1 对交付清单更严格，旧版输出可能拒绝验证。保留旧结果，使用其中的原始CSV和任务单重新渲染到新目录；不要篡改旧审计以伪装为新输出。

可用于 Agent 的提示词如下。English counterpart follows.

> 使用 scientific-figure-optimizer，检查 examples/spring.csv 和任务单，按许可的样式优化，在新目录输出 SVG/PDF/PNG、源数据、脚本及核查记录。解释确定性检查结果，并列出作者仍需确认的科学问题。

> Use scientific-figure-optimizer to inspect examples/spring.csv and its brief, apply only authorized styling, and deliver SVG/PDF/PNG, source data, script and audit in a new folder. Explain deterministic checks and identify scientific questions requiring author review.

## 发布与许可

代码和独立编写的说明使用 MIT，公开示例 CSV 使用 CC0-1.0。第三方依赖保留各自许可，见 references/capabilities.md。未打包 R2 原文、论文图片、真实锚杆数据、Origin 工程或私人路径。真实研究案例应存放于仓库外的私有目录。

使用方法见 [使用流程](docs/WORKFLOW.md) 和 [完整教程](docs/TUTORIAL.md)，本版验证范围见 [0.1.3 验证与限制](docs/VALIDATION-0.1.3.md)。共享或再次发布前，重新核对文件清单、数据使用权及目标可见范围。

命令行脚本没有上传数据的逻辑，但交付目录包含完整 CSV（包括未绘制的列）、来源和任务说明。Agent 若打开私人数据或图件，其内容会进入对话上下文。不要把“程序在本机绘图”理解为“AI 服务永远接触不到输入”。共享、发给模型或上传 GitHub 前均需审核；私有仓库也属于外部传输。

## 状态与局限

仅支持共用线性坐标轴的 1—3 条 CSV 曲线。缺单位、空值、非数值、NaN/Inf、越界显示、未知配置和处理请求均停止。程序保留全部数据与点序。科学含义、灰度可辨性、交叠文字、最终观感和期刊适配仍需人工核查。Origin、Word OLE、流程/机制图、照片、CAD 与数据处理尚未验收。现有验证证明有限案例上的可运行性，尚无用户研究、盲评或普遍提效证据。

Origin 基础导出和水印复查曾通过；后续出现文本、字体及进程退出问题，原生路线仍未通过验收，实验适配器未装入本发布。不能用基础案例推断一般稳定性。详见 [Origin 状态及复核边界](references/origin-assessment.md)。正式绘图路线仍为 Python/Matplotlib，PDF核查覆盖嵌套资源及本版新增的Type3支持。

0.1.3修复嵌入Type3字体被误报的问题，检查CharProcs字形流、显式编码及必要资源，仍不代表完整PDF标准或版式批准。修订见 [0.1.3说明](docs/RELEASE-0.1.3.md)，当前公开输出在 examples/expected-v0.1.3。十点独立数据为0.1.2构造，本版复用并重新运行；不能称为本版新构造数据。旧版记录和输出仅作历史保留。
