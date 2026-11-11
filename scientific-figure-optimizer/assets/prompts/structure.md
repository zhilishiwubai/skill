# 结构、装配与剖面 / Structure, assembly and sections

与[共同模板](common.md)组合。检索功能：`structure`；当前主要交付结构方案。

## 中文

```text
图型补充：结构图。视图需求：[整体 / 装配 / 剖面 / 爆炸 / 局部放大]。
以我提供的真实结构资料为内容依据，核对零件身份、连接/接触关系、装配顺序、轴线、尺寸和单位。只画资料中存在的杆体、套筒、锥体、缓冲件等，不因参考图出现过就补进本模型。缺尺寸或连接依据时列未知项，必要时仅做不按比例的示意方案，不编造可制造尺寸。

先安排整体定位，再用剖切位置或局部放大解释关键结构。相同零件跨视图保持一致编码；颜色表示部件身份，虚线/引线/剖面线的意义分别说明。剖切面与对应视图、遮挡与内部结构必须一致，爆炸位移不能被误解为实际间隙。不要让透视效果掩盖接触或装配关系。

标签采用可编辑文字，零件名称一一对应，引线尽量分层并避免交叉；只标注有依据的尺寸、公差、比例尺和方向。参考图只提供信息层级和表达规则，不照抄独特设备几何、原作者图标或尺寸。

交付视图列表、部件映射表、布局/编码/标注方案和结构待确认项。可编辑SVG示意、真实3D CAD和可计算有限元几何是不同要求。当前Skill没有这些图的绘制/CAD后端；无单独可用且已授权的路线时停在Figure Brief，不把位图称作可编辑模型。
```

## English

```text
Figure supplement: structure. Required views: [overall / assembly / section / exploded / detail].
Use the supplied actual design as the content authority. Verify component identity, joints/contacts, assembly order, axes, dimensions and units. Include rods, sleeves, cones or buffers only when supported by those sources. Missing dimensions or connection evidence remain unknown; a non-scale schematic plan may be appropriate, but manufacturing dimensions cannot be invented.

Establish the overall view before sections or details. Keep component identity encoding consistent across views and distinguish the meanings of color, hidden lines, leaders and hatching. Section planes must match their views; internal geometry and occlusion must agree. Exploded offsets are not actual clearances. Perspective must not conceal contacts or assembly relationships.

Use editable labels with one-to-one component names and orderly leaders. Add dimensions, tolerances, scales and directions only when supported. Borrow hierarchy and presentation rules without copying distinctive equipment geometry, icons or source dimensions.

Deliver a view list, component mapping, layout/encoding/annotation plan and unresolved structural questions. An editable SVG schematic, a real 3D CAD model and a computable FE geometry are different outputs. No such drawing/CAD backend ships here; without a separate authorized route, stop at the Figure Brief and never call a bitmap an editable model.
```
