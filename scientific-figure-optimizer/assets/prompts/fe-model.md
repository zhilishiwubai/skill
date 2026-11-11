# 有限元模型与结果 / Finite-element models and results

与[共同模板](common.md)组合。检索功能：`fe_model`；不包含求解器或结果生成能力。

## 中文

```text
图型补充：有限元模型/结果图。区分：[几何与简化 / 网格 / 接触和边界 / 已有结果云图 / 模型–试验对照]。
以真实模型、输入文件和求解记录核对单位制、材料、几何简化、单元/网格、接触、载荷/约束、步或时刻、收敛状态和结果变量。缺字段标未知，不能用论文截图补出本模型参数，也不假装已经计算或完成网格无关性验证。

把几何、网格、边界和结果信息分层表达。载荷/约束符号、坐标方向、接触对及剖切位置须对应模型；剖切示意不能伪装成实际内场。云图标明变量、单位、色条范围、视角及变形放大倍数；真实比例或放大倍数未知就不猜。

比较不同工况时，先核对同一变量、符号、单位、步/时刻和色标条件；需要不同范围时明确标出，不能利用各图自动缩放制造优劣。保留极值、负值、不收敛和局部异常；不靠裁切或换色条隐藏它们。只对已有结果做表达诊断，不从图片精确反算应力或生成“仿真结果”。

交付模型来源和条件表、面板/图层、色条与标注规则、结果可比性及待确认项。当前Skill不求解FE，也不产出原生FE工程；没有已授权的实际执行接口时仅交付Figure Brief和检查清单。
```

## English

```text
Figure supplement: FE model/results. Distinguish [geometry/simplification / mesh / contacts and boundaries / existing contour results / model–test comparison].
Use actual model/input files and solver records to check the unit system, materials, geometry assumptions, elements/mesh, contacts, loads/constraints, step/time, convergence and result variable. Missing fields remain unknown; paper screenshots cannot supply model parameters or establish calculations or mesh independence.

Separate geometry, mesh, boundary and result layers. Symbols, coordinates, contact pairs and section cuts must correspond to the model. A section schematic is not an actual internal field. Existing contours need variable, units, color limits, view and deformation magnification; unknown scaling cannot be guessed.

Before comparing conditions, align variables, signs, units, step/time and color limits. Disclose differing ranges instead of using automatic per-panel scaling to imply superiority. Retain extrema, negatives, nonconvergence and local anomalies; do not hide them with cropping or color limits. Diagnose existing results without reverse-engineering precise stresses from pixels or fabricating simulation output.

Deliver model provenance/conditions, panel/layer organization, colorbar/annotation rules, comparability limits and author questions. This Skill neither solves FE models nor creates native FE projects; without an authorized execution interface, deliver only the Figure Brief and checks.
```
