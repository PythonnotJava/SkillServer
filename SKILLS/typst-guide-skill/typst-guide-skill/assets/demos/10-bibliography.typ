// 10-bibliography.typ — 引用与参考文献
// 编译:
//   typst compile --root assets assets/demos/10-bibliography.typ
// 或在 assets 目录:
//   typst compile --root . demos/10-bibliography.typ

#set page(paper: "a5", margin: 1.4cm)
#set text(size: 10.5pt)
#set par(justify: true)
#set heading(numbering: "1.")

= 方法

我们采用冰川消融模型综述中的框架 @glacier-melt，并参考经典流体力学教材 @fluid-basics 中的连续介质描述。

数值实验细节见会议论文 @ice-sheet-model。

= 讨论

同一条目多次引用仍指向同一文献: @glacier-melt。

= 参考文献

#bibliography("/data/works.bib", title: "参考文献", style: "ieee")
