# 本地参考库：检索、视觉审阅与 Figure Brief

适用版本：Skill 0.2.2-local（沿用0.2.1的本地参考模块）；CSV renderer 仍为 0.1.3。本模块复用 Python 标准库 JSON、关键词/标签排序、SHA256 和现有 Pillow。没有网络调用、收费 API、向量服务、训练或网页服务。离线 HTML 只是缩略总览。脚本不会自己打开模型视觉工具，也不会自行声称看懂图片。

开始新任务时，按[图型提示词路由](prompt-routing.md)读取共同模板和实际类别补充，再执行以下检索、看图和采用流程。模板不等于案例卡，不替代实际视觉审阅。

## 存储与权限

可分发 Skill 只包含脚本、规范和空白模板。论文、衍生预览、私人数据、案例卡与根目录映射均放在独立本地库。配置路径由 `--library <库目录>` 或当前进程的 `SFO_REFERENCE_LIBRARY` 提供，不修改全局配置。库的 `library.json` 使用 `roots` 映射逻辑根到本机绝对目录；迁移时只调整这份本地配置。不要把个人绝对路径写进可分发 Skill。

用户允许本地参考不自动允许将图像传入模型上下文；先遵循当前任务权限。观看不等于复制发表授权。文章开放获取也不保证文中二次引图可重新使用。发布前单独确认文件清单、范围和目标。参考图与案例卡本身可能含私人信息，不能因为不是原 PDF 就自动公开。

## 库结构与字段

```
library.json          # schema_version=1, roots, source_file, cards
sources.json          # source_id -> 作者/年/标题/类型/定位/原件sha256
cards/CASE-ID.json    # 一独立图号一卡，case_id必须等于文件名
previews/             # 本地预览，不含上传动作
research-evidence.json # 可选，研究证据单列
index.json / index-cache.json  # 生成的索引与增量缓存
index.html / overview-*.jpg    # gallery生成的离线总览
```

`assets/reference-case-template.json` 描述案例卡字段。每卡需要来源作品身份、作者年与图号、PDF文件页（1开始）及定位方式、原页/预览路径和哈希、科学问题/主张/比较与证据、面板和阅读顺序、字体层级/配色/线型/形状编码、可借鉴规则及其ID、避免事项、适用/不适用场景、映射、来源与权利、视觉审阅及不确定性、编辑状态。没有实测不填写精确字号、色值或软件参数；明确标“未核查”。原文页码可另记，PDF文件页是稳定入口。

去重键是 `source_id + 规范图号`，不是文件名或仅字节哈希。同图不同清晰度和面板 6a/6b 不单独计数；跨页图的面板保留为一张完整卡。论文副本必须人工合并到同一 source_id。`duplicate_of` 可登记同图别名，但不计数、不检索、不采用；目标必须为同一独立图号的主卡。同一来源最多3个主案例。本轮目标20，不自动扩到1000。行政截图、付款记录和无关纹理不入库。

`VISUAL_REFERENCE` 的 mapping 必须为 `NOT_APPLICABLE_REFERENCE_ONLY`。真实实验/照片/结构证据用单列 `RESEARCH_EVIDENCE` 与 `mapping_status`，记录原路径及试件/工况/数据关联；缺关联时 UNMAPPED，不猜测。引用参考图不会变成本任务实测数据。

编辑等级分别为 `IMAGE_REFERENCE`、`DATA_AVAILABLE`、`NATIVE_PROJECT_PRESENT`、`NATIVE_REOPEN_VERIFIED`。后两级需要存在的原生工程及哈希；重开成功还需要本地 PASS 记录绑定同一工程哈希。记录存在仍不是工程真实性或科学含义的独立认证。PNG/SVG、截图和未经重开 OPJU 不算原生成功。本轮没有新增 Origin 后端。

## 执行步骤

以下命令在 Skill 目录执行，将 `<library>`、`<request.json>` 替换为自己的本地路径。依赖沿用 `requirements-lock.txt` 的 Python 3.12 环境，图库工具基础检索本身仅用标准库；gallery另需 Pillow。

```powershell
python scripts/reference_library.py --library <library> index --deep
python scripts/reference_library.py --library <library> search --query "锚杆缓冲耗能工作阶段" --function mechanism
python scripts/reference_library.py --library <library> read REF-004
python scripts/reference_library.py --library <library> brief <request.json> --out <new-task-folder>
python scripts/reference_library.py --library <library> gallery
python scripts/reference_library.py --library <library> validate --deep
```

`index` 必须成功后才能搜索。0.2.1使用索引schema 2，把配置、来源登记、卡片和研究证据登记的哈希绑定到索引。旧索引、损坏JSON或卡片改后未重建都会拒绝检索；审核修改后运行`index --deep`重建。该命令仅重建派生索引/缓存，可以恢复损坏缓存；不会修改原件、预览或审阅声明。每次检索还全量重算来源、预览与研究素材哈希，不能靠保留文件大小/时间戳隐藏改动。20例本地库可承担这个开销；不宣称适合任意规模。

检索结合科学表达功能、科学问题、适用场景、规则与标签，支持中英概念；不是 OCR、图像内容搜索或完整中文语义模型。默认不检索未视觉审阅案例。`--include-unreviewed` 仅登记待查候选，不能采用其规则。有限词表可能漏检，读者可用相关表达功能调整查询；不能用无关图片凑满3—5条。排序先考虑相关性，再尽量避免前几个结果来自同一作品。

英文词汇匹配过滤and/the/using等通用词，并按完整词匹配，避免line仅因出现在pipeline中而召回流程图。该过滤经过自编案例复测，不构成通用相关性或跨语言理解保证。

`read` 返回完整卡、卡哈希和预览路径/哈希。Agent随后必须用已授权查看方式实际打开图件。录入本任务观察后，将预览哈希填入 request 的 `viewed_preview_sha256`，选择卡中已有规则ID，说明 `applied_to`。至少两个来源；不足则填 `limited_sources_reason` 并得到 LIMITED_REFERENCE_PLAN。不能把脚本读取字节等同于看图。审阅字段是可追溯声明，不能机器证明人/模型确实看过；本轮实际查看的工具记录与任务记录相互佐证。

`brief` 返回方案与事件记录，包括 SEARCH、CASE_CARD_READ、PREVIEW_BYTES_READ、VISUAL_REVIEW_DECLARED、RULES_ADOPTED。预览改动、无效规则、UNMAPPED被作试件证据、缺第二来源说明、非法尺寸均停止。已有输出目录拒绝，写出失败清理本次临时目录，不保留看似成功的交付。Figure Brief是方案校验，不是审美、科学或期刊批准。

原 CSV CLI 不会自动调用图库；是 Agent 按 SKILL 执行检索/查看/方案，再调用原绘图 CLI。本次功能测试保留原CLI独立使用。需要绘图时，严格v1 `plot-brief.json`单独传给 `figure.py check/render/verify`，不把案例字段塞入旧任务单。共用单一纵轴后端不能冒充双轴或多面板。规则如无法落实到当前后端，方案应写明限制，不能悄悄改单位或删曲线。

## 完整性、检查与人工责任

增量模式按大小和mtime复用哈希；这不是防篡改机制。验收使用 `validate --deep` 全量重算原件与预览哈希。检查缺失路径、重复图号/预览、来源数、引用及编辑等级。原始作品元数据和卡片观察仍需作者/审阅者负责，哈希不能证明作者、年份、权利或科学主张真实。

执行后重读 SVG/PDF/PNG，并查看最终尺寸与灰度预览。自动检查可以判断路径、顶点、顺序、尺寸、字体资源和文件完整性；结构真实性、颜色语义、图例/标注交叠、灰度可辨和科学意义仍须实际视觉与作者判断。三个任务分别记录需求、3—5候选及理由、实际查看、所选case_id、两来源规则和新设计。不要统一标成自动通过。
