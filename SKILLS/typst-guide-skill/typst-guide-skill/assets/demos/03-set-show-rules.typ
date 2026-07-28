// 03-set-show-rules.typ — set / show 规则
// 编译: typst compile 03-set-show-rules.typ

#set page(paper: "a5", margin: 1.4cm)
#set text(size: 10.5pt)
#set par(justify: true, leading: 0.65em)
#set heading(numbering: "1.1")
#set list(indent: 1em, marker: ([•], [--]))
#set enum(indent: 1em)

// show: 定制一级标题外观
#show heading.where(level: 1): it => {
  set text(weight: "bold", size: 14pt)
  block(above: 1.1em, below: 0.7em)[
    #smallcaps[Section]
    #h(0.4em)
    #counter(heading).display()
    #h(0.4em)
    #it.body
  ]
}

#show link: underline
#show raw.where(block: true): it => block(
  width: 100%,
  fill: luma(95%),
  inset: 8pt,
  radius: 3pt,
  it,
)

= Set 与 Show

set 规则改变*后续*同类元素的默认参数；show 规则改写元素呈现。

== 段落与文本

本段应两端对齐。字体大小与行距由文件顶部 set 规则控制。

== 列表样式

- first
- second
  - nested

+ one
+ two

== 链接样式

#link("https://typst.app/docs")[文档链接会被 underline show 规则修饰]。

== 代码块样式

```typ
#set text(size: 12pt)
#show heading: strong
```
