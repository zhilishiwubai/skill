# 0.1.3 修复验证，2026-11-10

本版正式路线仍为Python/Matplotlib，不安装Origin实验适配器。Windows、Python3.12.14、PowerShell7.6.9，当前完全访问；不代表受限沙箱恢复。

正式代码修复：PDF Type3字体直接通过CharProcs嵌入字形，不必有FontDescriptor/FontFile。本版核查矩阵、范围、Widths结构、显式Differences编码与glyph对应、字形流/度量操作、必要资源。仅声明字体资源检查，不声明完整PDF标准合规。采用命名基础编码的Type3保守拒绝，需单独映射后再支持。

| 验证 | 证据与界限 |
|---|---|
| 正式自动回归 | 原32项+新增11项Type3，共43项通过；本轮显式提供既有真实导出PDF，原生程序未启动 |
| 实验代码回归 | 共55项通过，包含上述43项及换行/字体别名/退出检测等12项；不是与43项相加后的98个独立测试 |
| 实际Type3文件 | 既有科学计数PDF重新读取，2项Type3+4项TrueType资源获识别；原PDF页面裁切仍被独立布局检查拒绝 |
| 换行 | 仅LF/CRLF约定等价，其他字符、空格或科学含义变化仍拒绝；保留原始输入与原生读回文本 |
| 字体别名 | 从同一已解析字体文件的family名称取得“微软雅黑”，未改系统字体、未用Arial替代；本机字体元数据与模拟查询回归通过 |
| 退出保护 | PID+创建时间确认拥有权，API未报错但PID仍在即失败；模拟驻留、正常退出、PID复用、已有会话和并发实例均获检查；未证明实际原生退出已修复 |

正常安装后可运行教学模板及公开示例，具体文件核对、输出及包哈希见发布清单与本地交付记录。可执行命令：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts/figure.py render examples/spring.json --out runs/new-spring
.venv\Scripts\python.exe scripts/figure.py verify runs/new-spring
```

仓库公开测试未包含原生PDF夹具时，实际导出文件测试明确SKIP，其余42项可运行；提供环境变量SFO_NATIVE_TYPE3_PDF后该项执行。指定路径无效会失败，不悄悄跳过。公开运行不得把SKIP称为通过。

已知原生环境阻断：官方最小Application→Exit(True)→删除对象→gc仍驻留；初次探针误调用不支持的IsValid也单独记录，未用于证明Exit失败。随后正确探针仍驻留才构成反证。用户选择保留9个记录在案的进程；之后没有新增Origin实例或强制结束进程。没有新原生端到端验收，科学计数版式仍未修复/批准。未修改许可、安全设置、COM注册或软件安装。

本版不重复宣称0.1.2的双新环境独立复现已重新执行。历史实测保留，有限新运行按本版实际日志报告。科学含义、版权来源、统计、B1敏感性和所有视觉质量仍需人工判断；GitHub未上传。
