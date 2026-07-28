// template.typ — 可复用文档模板函数

#let conf(
  title: none,
  authors: (),
  abstract: none,
  body,
) = {
  set document(
    title: if title == none { "" } else { title },
    author: authors,
  )
  set page(
    paper: "a5",
    margin: 1.5cm,
    numbering: "1",
  )
  set text(size: 10.5pt)
  set par(justify: true, first-line-indent: 1.2em)
  set heading(numbering: "1.1")

  align(center)[
    #text(15pt, weight: "bold")[
      #if title == none [Untitled] else [#title]
    ]
    #v(0.5em)
    #if authors.len() > 0 {
      text(10pt)[#authors.join(" · ")]
      v(0.3em)
    }
  ]

  if abstract != none {
    block(inset: 8pt, fill: luma(96%), width: 100%)[
      #text(weight: "bold")[Abstract.]
      #h(0.3em)
      #abstract
    ]
    v(0.6em)
  }

  body
}
