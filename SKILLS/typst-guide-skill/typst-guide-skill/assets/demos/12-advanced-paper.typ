// 12-advanced-paper.typ — 进阶论文风示意（双栏、摘要、图、公式）
// 编译: typst compile 12-advanced-paper.typ

#set document(title: "Glacier Flow Notes", author: "Guide Author")
#set page(
  paper: "a4",
  margin: (x: 1.6cm, y: 1.8cm),
  columns: 2,
  numbering: "1",
)
#set text(size: 9.5pt)
#set par(justify: true, leading: 0.55em)
#set heading(numbering: "1.")
#set math.equation(numbering: "(1)")

#place(
  top,
  float: true,
  scope: "parent",
  clearance: 1em,
)[
  #align(center)[
    #text(14pt, weight: "bold")[A Compact Note on Glacier Flow]
    #v(0.35em)
    #text(9pt)[Guide Author · Typst Guide Skill]
    #v(0.5em)
  ]
  #block(inset: (x: 0.5em), width: 100%)[
    #text(weight: "bold")[Abstract.]
    #h(0.25em)
    #lorem(45)
  ]
  #v(0.4em)
]

= Introduction

#lorem(55)

= Methods

我们使用简化质量守恒关系，并与经验参数化结合。

$ Q = rho A v + C $ <eq-q>

如 @eq-q 所示，流量由密度、截面积与速度主导。

#figure(
  table(
    columns: 2,
    align: (left, right),
    stroke: 0.4pt,
    inset: 4pt,
    table.header([Symbol], [Meaning]),
    [$Q$], [discharge],
    [$rho$], [density],
    [$A$], [area],
    [$v$], [velocity],
  ),
  caption: [Notation],
) <tab-not>

= Results

#figure(
  rect(width: 100%, height: 2.6cm, fill: luma(93%), stroke: 0.5pt)[
    #align(center + horizon)[Result plot placeholder]
  ],
  caption: [Synthetic profile],
)

#lorem(40)

= Conclusion

#lorem(28)
