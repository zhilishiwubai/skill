# 使用流程

1. 准备带表头的 UTF-8 CSV，并保留原件。明确每列单位、数据来源与使用权、要回答的问题及图支持的结论。程序支持共用线性坐标的 1—3 条曲线；不进行平滑、删点、排序、重采样或换单位。
2. 复制 `assets/brief-template.json`，填写输入路径、列名、来源、证据等级、单位、样式授权和验收问题。路径相对任务单解析。只有任务单许可的样式字段才能修改；缺单位或科学含义不清时先澄清。
3. 按 README 用 Python 3.12 创建环境并安装锁定依赖。执行 `python scripts/figure.py check brief.json`；这只验证输入，不能证明字体或导出通过。
4. 执行 `python scripts/figure.py render brief.json --out runs/new-result`，再执行 `python scripts/figure.py verify runs/new-result`。输出目录必须不存在；失败码为 2。成功结果包括图件、原 CSV 快照、任务单、代码、依赖和审计。
5. 打开实际 `figure.png`、`final-size.png`、`grayscale.png`；检查遮挡、裁切、线型、灰度可辨性、峰值与负值可见性。SVG 顶点读回、PDF 尺寸和字体、PNG 像素和 DPI 的 PASS 不等于科学结论或期刊批准。
6. 将整个结果目录复制到其他位置，按其中 `REPRODUCE.md` 新建环境并重跑。自定义字体需独立合法安装；程序记录字体哈希，不能靠删除哈希冒充一致复现。

每次修改使用新目录。`verify` 会拒绝缺失/变化的必要文件并将存储的 PASS 改为 FAIL；审计不是数字签名，不能防止有意同时篡改多个记录。不要把含私人信息的结果目录直接上传。

可以给 Agent 的请求：

> 使用 scientific-figure-optimizer 检查这份 CSV 与任务单，保留全部数值及点序，只执行获准的样式修改，在新目录交付 SVG/PDF/PNG 和独立复现文件，并解释仍需作者确认的问题。

> Use scientific-figure-optimizer to check this CSV and brief, preserve all values and point order, apply only authorized styling, and deliver SVG/PDF/PNG with standalone reproduction files in a new directory. Identify questions that still require author review.

Origin 当前未通过扩展验收，不属于安装包的绘图后端；详见 `references/origin-assessment.md`。不需要安装或重装 Origin 才能使用本 Python 流程。


## 0.2.0-local 本地参考扩展

科研制图任务现在先进行问题确认、相关案例检索、授权视觉查看、两来源规则采用和Figure Brief记录，再走原CSV流程。结构/机理/装置/流程只完成参考与方案，不新增绘图后端或Origin适配器。详见 [本地参考工作流](../references/local-reference-library.md)。原严格v1绘图任务单保持独立；新增模板为assets/reference-*.json，私人案例库不随安装分发。
