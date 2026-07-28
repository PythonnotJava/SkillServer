// 11-template/main.typ — 模板使用方
// 编译: typst compile main.typ
// （在 11-template 目录内）

#import "template.typ": conf

#show: conf.with(
  title: "Making a Template",
  authors: ("Ada Lovelace", "Typst Guide"),
  abstract: [
    演示如何把 set/show 与标题区封装进可复用函数，并在主文件用
    `#show: conf.with(...)` 套用。
  ],
)

= 引言

模板把重复版式从内容中剥离。主文件只关心章节与论述。

= 设计要点

+ 用 `#let conf(...) = { ... }` 接收命名参数与 `body`
+ 在函数内集中 `set` 规则
+ 主文件 `#show: conf.with(...)` 应用模板

= 结论

分文件模板便于团队统一风格。
