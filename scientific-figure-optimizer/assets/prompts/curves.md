# 定量数据曲线 / Quantitative curves

与[共同模板](common.md)组合。检索功能：`curves`；执行边界：符合v1合同的CSV线性曲线。

## 中文

```text
图型补充：定量曲线。子型：[荷载–位移 / 应力–应变 / 时间历程 / 加载功或耗能量 / 其他]。
明确x列、各y列、物理量、单位、系列标签、测量或计算来源，以及已有不确定性。能量类必须有授权的原始结果或可追溯计算依据；不能因为曲线面积可计算就自动积分或把加载功当作不可逆耗散。

保留每个有效点和输入次序，包括重复、逆序、负值和不利结果；不自动平滑、排序、删点、拟合、重采样、归一化或换单位。缺失/非有限值按位置停止，不插补。缺不确定性时不造误差带。

选择线型与颜色的冗余编码，说明图例、直接标注或参考线对读者问题的作用。范围包含所有点；峰值、负值、回折和参考边界不能被裁掉或移动。百分比应变/延伸率不冒充位移。参考线保留数值、来源和未验证状态；未得到来源支持的峰值/失效标记不添加。

只有1—3条、相同y单位和共享线性轴符合当前执行路线时，生成独立v1任务单并依次check/render/verify。散点、柱图、箱线、直方图、热图、双轴、多面板及额外处理请求需单独说明未受支持的部分，先完成方案；不能静默删曲线或改数据以适配。

交付数值/点序/参考位置的导出后核查、物理尺寸与字体说明，以及实际彩色、最终尺寸和灰度观察。审美判断、统计合理性和科学边界解释交由作者确认。
```

## English

```text
Figure supplement: quantitative curves. Subtype: [load–displacement / stress–strain / time history / loading work or energy / other].
Identify x and y columns, quantities, units, series labels, measurement/calculation provenance and existing uncertainty. Energy requires authorized results or a traceable calculation; do not automatically integrate a curve or equate loading work with irreversible dissipation.

Preserve every valid point and input order, including repeated/reversed x, negatives and unfavorable results. Do not silently smooth, sort, remove, fit, resample, normalize or convert units. Stop on missing/nonfinite selected values with their location; do not impute them or invent uncertainty bands.

Use redundant color and line-pattern encoding. Explain the purpose of legends, direct labels and reference lines. Limits must include all points, peaks, negatives and reversals. Preserve reference values, sources and unverified status. Percentage strain/elongation is not displacement, and unsupported failure markers cannot be added.

Execute check/render/verify through a separate strict v1 brief only for 1–3 series with the same y unit and shared linear axes. Scatter, bar, box, histogram, heatmap, dual-axis, multipanel or additional processing requests require an explicit unsupported-scope statement and a plan; do not drop curves or alter data to fit the backend.

Deliver actual export readback of values/order/reference positions, dimensions and font requirements, plus observed color/final-size/grayscale results. Statistical interpretation, aesthetics and scientific boundary meaning remain author decisions.
```
