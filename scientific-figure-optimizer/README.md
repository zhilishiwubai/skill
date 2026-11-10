# Scientific figure optimizer 0.2.1-local

新增本地科学图形参考检索、实际视觉审阅和 Figure Brief 工作流；CSV renderer 保持 0.1.3。将 CSV 科研曲线及任务单转换为可复现、可编辑的数据图。Agent 负责理解修改请求、建立任务单、解释诊断及组织人工核查，Python 程序负责保真绘图与确定性检查。

## 安装

使用 Python 3.12。先确认 `python --version`，再建立独立环境，在仓库根目录运行。锁文件针对 Python 3.12；系统默认 Python 3.10 不能代替本轮隔离安装验收。不要因此更改全局 Python 或关闭沙箱。

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

仓库只是待审核内容。上传前列出具体文件、目标和可见范围并取得明确确认。

本次发布候选目标为 `zhilishiwubai/skill`，2026-11-10实际读取到的可见性为public。文件清单确认前不上传或推送；本地私人图库、论文预览和研究数据不属于公开候选。

命令行脚本没有上传数据的逻辑，但交付目录包含完整 CSV（包括未绘制的列）、来源和任务说明。Agent 若打开私人数据或图件，其内容会进入对话上下文。不要把“程序在本机绘图”理解为“AI 服务永远接触不到输入”。共享、发给模型或上传 GitHub 前均需审核；私有仓库也属于外部传输。

## 状态与局限

Origin当前状态：作者经代码审阅确认可用，并要求本轮停止复验；这一决定与保留的自动运行记录分别记录。本包仍只安装Python绘图与本地参考工具，不新增Origin可执行适配器。最近一次代码回归为68项（67通过、1项可选Origin PDF检查跳过）；本次仅整理说明和发布候选，没有重跑Origin。

仅支持共用线性坐标轴的 1—3 条 CSV 曲线。缺单位、空值、非数值、NaN/Inf、越界显示、未知配置和处理请求均停止。程序保留全部数据与点序。科学含义、灰度可辨性、交叠文字、最终观感和期刊适配仍需人工核查。Origin、Word OLE、流程/机制图、照片、CAD 与数据处理尚未验收。现有验证证明有限案例上的可运行性，尚无用户研究、盲评或普遍提效证据。

Origin 基础导出和水印复查曾通过；后续出现文本、字体及进程退出问题，原生路线仍未通过验收，实验适配器未装入本发布。不能用基础案例推断一般稳定性。详见 [Origin 状态及复核边界](references/origin-assessment.md)。正式绘图路线仍为 Python/Matplotlib，PDF核查覆盖嵌套资源及本版新增的Type3支持。

0.1.3修复嵌入Type3字体被误报的问题，检查CharProcs字形流、显式编码及必要资源，仍不代表完整PDF标准或版式批准。修订见 [0.1.3说明](docs/RELEASE-0.1.3.md)，当前公开输出在 examples/expected-v0.1.3。十点独立数据为0.1.2构造，本版复用并重新运行；不能称为本版新构造数据。旧版记录和输出仅作历史保留。


## 本地科学参考工作流（0.2.0-local）

先理解问题与证据，再检索3—5个相关案例、实际打开选定预览、从至少两个来源提炼规则，写Figure Brief，然后在支持范围内绘图与核查。这是运行时参照，不是训练。结构、机理、装置与流程支持参考方案；确定性绘图仍仅支持CSV曲线。PPT排版由演示文稿工具负责。

参考 [详细使用说明与数据结构](references/local-reference-library.md)。配置自己的本地库后，在Skill目录运行：

```powershell
python scripts/reference_library.py --library <library> index --deep
python scripts/reference_library.py --library <library> search --query "荷载位移对比" --function curves
python scripts/reference_library.py --library <library> read <case_id>
python scripts/reference_library.py --library <library> brief <request.json> --out <new-task-folder>
python scripts/reference_library.py --library <library> gallery
```

先用授权查看方式打开原图，才填写观察、预览哈希和规则采用。脚本读到图片字节不代表完成视觉审阅。模板在assets/reference-*.json；这些是待填模板，不是现成案例库。库配置使用逻辑根映射，本机路径只写在外部本地library.json中。安装包不包含本次私人来源、预览、卡片或配置。

给Agent的中英提示词：

> 使用 scientific-figure-optimizer，连接我指定的本地参考库。先明确问题、读者、图型、尺寸与编辑要求，检索3—5个相关案例并解释理由。在已获授权的范围内实际查看选定预览，从两个不同来源采用规则，记录case_id、观察和本任务新设计，生成Figure Brief。仅使用真实任务数据；超出后端能力时明确停在方案。

> Use scientific-figure-optimizer with my configured local reference library. Establish the scientific question, reader, figure type, physical size and editing needs. Retrieve 3–5 relevant cases with reasons, actually view selected previews within current permissions, and adopt rules from two source works into a Figure Brief. Record case IDs, observations and new design. Use only actual task data and stop at planning when execution is unsupported.


0.2.1-local复测修复：索引采用schema 2并绑定卡片/配置哈希；损坏或过期索引拒绝检索，检索前全量校验原件与预览。旧索引需审核修改后执行index --deep重建，不能直接继续使用。错误嵌套类型按明确字段报错并返回2。CSV renderer仍为0.1.3，旧结果保留。
