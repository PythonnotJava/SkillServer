// 05-math.typ — 数学模式常用写法
// 编译: typst compile 05-math.typ

#set page(paper: "a5", margin: 1.4cm)
#set text(size: 11pt)
#set heading(numbering: "1.")

= 数学排版

== 行内与独立

行内: 流量 $Q = rho A v + C$。

独立（公式两侧空格）:

$ Q = rho A v + C $

== 上下标、分数、求和

$ 7.32 beta + sum_(i=0)^nabla (Q_i (a_i - epsilon)) / 2 $

== 向量、矩阵、分段

$ v := vec(x_1, x_2, x_3) $

$ mat(1, 2, 3; 4, 5, 6; 7, 8, 9) $

$ f(x) = cases(
  0 & "if" x < 0,
  1 & "if" x >= 0,
) $

== 根式、二项式、可伸缩括号

$ sqrt(a / b) + root(3, x) + binom(n, k) $

$ lr(angle.l (A + B) / 2 angle.r) $

== 多字母变量与对齐

$ Q = rho A v + "time offset" $

$ p(x) &= x^2 + 2x + 1 \
      &= (x + 1)^2 $

== 编号公式（figure 包一层也可）

#set math.equation(numbering: "(1)")

$ integral_0^1 x^2 dif x = 1/3 $ <eq-int>

引用公式 @eq-int。
