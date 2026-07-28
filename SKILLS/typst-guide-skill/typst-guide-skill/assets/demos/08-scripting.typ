// 08-scripting.typ — 变量、函数、条件、循环
// 编译: typst compile 08-scripting.typ

#set page(paper: "a5", margin: 1.3cm)
#set text(size: 10.5pt)
#set heading(numbering: "1.")

= 脚本能力

== 绑定与函数

#let site = "Alpha"
#let speed(year) = 100 + 3 * year
#let badge(body) = box(
  fill: luma(92%),
  inset: (x: 6pt, y: 3pt),
  radius: 3pt,
  body,
)

站点 #badge[*#site*] 第 5 年速度估计为 *#speed(5)* m/year。

== 条件

#let draft = true
#if draft [
  #text(fill: rgb("#a40"))[(草稿水印示意)]
] else [
  正式版
]

== 循环

#let layers = ("雪", "粒雪", "冰川冰")
#for (i, name) in layers.enumerate() [
  + 第 #str(i + 1) 层: #name
]

== 数组与字典

#let conf = (
  title: "Scripting Demo",
  n: 3,
  flags: (show_plot: true, bilingual: false),
)

标题: #conf.title；重复次数: #conf.n。

#for k in range(1, conf.n + 1) [
  - item \##k
]

== 内容拼接

#let note(body) = [
  #set text(9pt, fill: luma(30%))
  #block(inset: 8pt, stroke: (left: 2pt + luma(60%)), body)
]

#note[
  在 markup 中用 `#` 切入代码；在代码块中直接写表达式。
  复杂逻辑优先 `#let` 成函数，保持正文干净。
]
