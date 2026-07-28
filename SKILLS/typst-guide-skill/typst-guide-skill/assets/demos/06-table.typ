// 06-table.typ — 表格指南精简版
// 编译: typst compile 06-table.typ

#set page(paper: "a5", margin: 1.3cm)
#set text(size: 10pt)
#set heading(numbering: "1.")

= 表格

== 基础表

#figure(
  table(
    columns: 3,
    align: (left, center, right),
    stroke: 0.5pt,
    inset: 6pt,
    table.header([站点], [速度 (m/y)], [状态]),
    [Alpha], [120], [稳定],
    [Beta], [85], [退缩],
    [Gamma], [150], [前进],
  ),
  caption: [基础三列表],
) <tab-basic>

见表 @tab-basic。

== 列宽与填充

#table(
  columns: (1fr, 2fr, 60pt),
  align: horizon,
  fill: (_, y) => if y == 0 { luma(90%) } else if calc.odd(y) { luma(97%) },
  stroke: (x, y) => if y == 0 { (bottom: 0.8pt) } else { (bottom: 0.3pt + luma(80%) ) },
  [ID], [说明], [值],
  [1], [年平均厚度], [250 m],
  [2], [末端流速], [3.1 m/d],
  [3], [物质平衡], [-0.4 m w.e.],
)

== 合并单元格

#table(
  columns: 3,
  stroke: 0.5pt,
  table.cell(colspan: 3, align: center, fill: luma(92%))[*区域汇总*],
  [北坡], [中部], [南坡],
  table.cell(rowspan: 2, align: horizon)[观测],
  [OK], [OK],
  [OK], [Fail],
)

== 与 figure 联动编号

#set figure.caption(position: top)
#figure(
  table(
    columns: 2,
    [参数], [取值],
    [$rho$], [$917 "kg/m"^3$],
    [$g$], [$9.81 "m/s"^2$],
  ),
  caption: [物理参数],
)
