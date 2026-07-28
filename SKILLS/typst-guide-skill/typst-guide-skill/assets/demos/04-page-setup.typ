// 04-page-setup.typ — 页面、页眉页脚、页码
// 编译: typst compile 04-page-setup.typ

#set document(title: "Page Setup Demo", author: "Typst Guide")
#set text(size: 10.5pt)
#set par(justify: true)
#set heading(numbering: "1.")

#set page(
  paper: "a5",
  margin: (top: 2.2cm, bottom: 2cm, x: 1.5cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8.5pt, fill: luma(40%))
      grid(
        columns: (1fr, 1fr),
        align(left)[Page Setup Demo],
        align(right)[Typst Guide Skill],
      )
      v(-0.3em)
      line(length: 100%, stroke: 0.4pt + luma(70%))
    }
  },
  footer: context {
    set text(9pt)
    align(center)[
      #counter(page).display("第 1 页 / 共 1 页", both: true)
    ]
  },
)

// 首页可单独处理
#align(center)[
  #v(1.5cm)
  #text(16pt, weight: "bold")[页面设置示例]
  #v(0.4em)
  #text(10pt)[页眉 · 页脚 · 页码 · 边距]
  #v(1cm)
]

#pagebreak()

= 边距与纸张

通过 `#set page(paper: ..., margin: ...)` 控制纸张与边距。命名边距字典可分别设置上下左右。

= 页眉页脚

页眉页脚里常用 `context` 读取页码计数器。本页起应能看到页眉。

= 分栏（示意）

#columns(2, gutter: 12pt)[
  #lorem(40)
  #colbreak()
  #lorem(40)
]

= 单次页面修改

#page(flipped: true, margin: 1cm)[
  = 横向单页
  使用 `#page(...)[...]` 可对单页做一次性修改（如横向表）。
  #lorem(20)
]
