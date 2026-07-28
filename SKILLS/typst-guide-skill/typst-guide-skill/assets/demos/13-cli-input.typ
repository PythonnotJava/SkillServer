// 13-cli-input.typ — 使用 CLI --input 注入变量
// 编译:
//   typst compile 13-cli-input.typ
//   typst compile 13-cli-input.typ --input title="My Title" --input author="Ada" --input draft=true

#set page(paper: "a6", margin: 1.1cm)
#set text(size: 10.5pt)

#let title = sys.inputs.at("title", default: "CLI Input Demo")
#let author = sys.inputs.at("author", default: "Anonymous")
#let draft = sys.inputs.at("draft", default: "false") == "true"

#if draft [
  #set page(background: rotate(24deg, text(48pt, fill: rgb(255, 0, 0, 40))[DRAFT]))
]

#align(center)[
  #text(13pt, weight: "bold")[#title]
  #v(0.3em)
  #author
]

= 说明

`sys.inputs` 接收 `typst compile --input key=value` 传入的字符串。

当前值:

- title: #title
- author: #author
- draft: #if draft [true] else [false]

适合 CI 多环境构建、封面信息注入、草稿水印开关。
