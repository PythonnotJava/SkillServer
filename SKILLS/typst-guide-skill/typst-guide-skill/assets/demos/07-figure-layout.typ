// 07-figure-layout.typ — 图、对齐、布局容器
// 编译: typst compile 07-figure-layout.typ

#set page(paper: "a5", margin: 1.3cm)
#set text(size: 10.5pt)
#set heading(numbering: "1.")
#set par(justify: true)

= 图与布局

== 占位图（无外部图片依赖）

#figure(
  rect(width: 80%, height: 3.2cm, fill: gradient.linear(blue.lighten(70%), aqua), stroke: 0.6pt)[
    #align(center + horizon)[
      #text(12pt, weight: "bold")[Glacier Schematic]
      #v(0.2em)
      #text(9pt)[replace with #raw("#image(\"photo.jpg\")")]
    ]
  ],
  caption: [无外部文件时的示意图占位],
) <fig-schematic>

见图 @fig-schematic。若有真实图片:

```typ
#figure(
  image("glacier.jpg", width: 70%),
  caption: [_Glaciers_ are critical to climate systems.],
) <glaciers>
```

== 并排布局

#grid(
  columns: (1fr, 1fr),
  gutter: 10pt,
  figure(
    square(size: 2.4cm, fill: red.lighten(75%), stroke: 0.5pt),
    caption: [A],
  ),
  figure(
    circle(radius: 1.2cm, fill: green.lighten(75%), stroke: 0.5pt),
    caption: [B],
  ),
)

== Stack / 对齐 / 间距

#align(center)[
  #stack(
    dir: ltr,
    spacing: 8pt,
    box(width: 1.2cm, height: 1.2cm, fill: luma(85%)),
    box(width: 1.2cm, height: 1.8cm, fill: luma(70%)),
    box(width: 1.2cm, height: 1.0cm, fill: luma(55%)),
  )
]

#v(0.8em)
#line(length: 100%, stroke: 0.4pt + luma(60%))

== Place（角标示意）

#box(width: 100%, height: 2.5cm, stroke: 0.4pt + luma(70%))[
  #place(top + right, dx: -4pt, dy: 4pt)[
    #set text(8pt)
    badge
  ]
  #align(center + horizon)[内容区]
]
