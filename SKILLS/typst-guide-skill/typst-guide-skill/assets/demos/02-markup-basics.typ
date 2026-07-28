// 02-markup-basics.typ — 标题/列表/强调/链接/代码
// 编译: typst compile 02-markup-basics.typ

#set page(paper: "a5", margin: 1.5cm)
#set par(justify: true)
#set heading(numbering: "1.")

= Markup 基础

== 强调与代码

普通段落。*粗体*、_斜体_、*_粗斜体_*、#underline[下划线]、#strike[删除线]。

行内代码: `let x = 1`。

代码块:

```python
def flow(q, a):
    return q / a
```

== 列表

无序:

- 气候
  - 温度
  - 降水
- 地形
- 地质

有序:

+ 采集数据
+ 建立模型
+ 验证结果

术语列表:

/ Typst: 现代标记排版系统
/ Markup: 默认正文模式
/ Set rule: 设置元素默认参数

== 链接与脚注

访问 #link("https://typst.app")[Typst 官网]。#footnote[这是脚注示例。]

引用稍后标签: 见 @sec-review。

== 引用块

#quote(block: true, attribution: [Typst Docs])[
  Typst combines powerful automation and high-quality typography with speed and ease of use.
]

== Review <sec-review>

本节覆盖日常写作最常用的 markup。
