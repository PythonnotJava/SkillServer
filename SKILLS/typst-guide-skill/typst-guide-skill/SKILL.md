# Typst Guide Skill

全局可复用的 Typst 排版与命令行技能。帮助 AI 与用户快速编写、格式化、编译 Typst 文档，并参考 `assets/` 中的可运行示例。

> 文档基准：Typst 官方文档结构（Tutorial / Reference / Guides）  
> 本地 CLI 探测：以当前环境 `typst --version` 为准（示例按 0.12+ 兼容写法）

---

## 用途

当用户需要以下能力时启用本技能：

- 用 Typst 写论文、报告、作业、幻灯片式文稿、书籍章节
- 从零创建 `.typ` 项目，或改造现有 Typst 文档
- 配置页面、页眉页脚、目录、标题编号、中英混排
- 写数学公式、表格、图片、引用/参考文献
- 编写可复用模板（`#let conf(...)` / 分文件 `#import`）
- 使用 Typst CLI：`compile` / `watch` / `query` / `fonts` / `update`
- 导出 PDF / PNG / SVG（及新版本支持的 HTML/bundle，若 CLI 可用）
- 排查编译错误、字体缺失、路径、包导入问题

---

## 触发条件

满足任一即可主动应用本技能：

- 用户提到 Typst / `.typ` / typst compile / 排版替代 LaTeX
- 需要生成可编译的排版源码（论文、报告、作业、简历草稿等）
- 需要表格、公式、参考文献、模板化文档结构
- 需要 CLI 命令、监听编译、查询文档元素、导出多格式

---

## 工作原则

1. **优先给可编译源码**：默认输出完整 `.typ`（含必要 `set`/`show`），不要只给碎片。
2. **先查环境**：执行 `typst --version`；需要字体时 `typst fonts`；编译用 `typst compile`。
3. **参考 assets**：优先复用/改编 `assets/demos/` 示例，而不是从零瞎写。
4. **版本兼容**：未知版本时避免最新实验特性；优先 0.12+ 稳定 API。
5. **中文文档**：设置 CJK 字体（如 `Noto Serif CJK SC` / `Source Han Serif SC` / Windows `SimSun`），并说明字体缺失时如何替换。
6. **资源路径**：图片、CSV、Bib 使用相对路径；演示优先用内置图形/`lorem`，减少外部依赖。
7. **安全**：不写入密钥；不把用户私密 bib/数据默认提交到公共包路径。

---

## Typst 核心心智模型

### 三种模式

| 模式 | 进入方式 | 用途 |
|------|----------|------|
| Markup | 默认 | 正文、标题、列表、强调 |
| Math | `$...$` | 公式 |
| Code | `#...` 或代码块 `{}` | 变量、函数、控制流、set/show |

### 最常用标记

```typ
= 一级标题
== 二级标题
*粗体*  _斜体_  `code`
- 无序列表
+ 有序列表
/ 术语: 定义
@label  引用
#figure(...) <label>
```

### set / show

```typ
// set：设置某类元素的默认参数
#set text(font: "New Computer Modern", size: 11pt)
#set page(paper: "a4", margin: (x: 2cm, y: 2cm))
#set heading(numbering: "1.1")
#set par(justify: true, leading: 0.65em)

// show：改写某类元素的呈现
#show heading.where(level: 1): it => {
  set text(weight: "bold", size: 16pt)
  block(above: 1.2em, below: 0.8em, it)
}
#show link: underline
```

### 内容块 vs 字符串

- `[markup 内容]`：content block
- `"纯字符串"`：string（路径、键名等）
- 函数在 markup 中以 `#name(...)` 调用；在 code/math 中通常不需要 `#`

---

## 命令行工具（CLI）

### 安装与版本

```bash
typst --version
typst help
typst help compile
```

常见安装来源：

- 官方发布页 / GitHub Releases
- `winget install --id Typst.Typst`（Windows）
- `cargo install --locked typst-cli`
- 包管理器（scoop/choco/brew 等，��平台而定）

### 编译

```bash
# 基础：.typ -> PDF
typst compile main.typ
typst compile main.typ out/main.pdf

# 指定根目录（多文件项目）
typst compile --root . src/main.typ

# 注入输入变量（脚本/CI）
typst compile --input author="Alice" --input draft=true main.typ

# 字体路径
typst compile --font-path ./fonts main.typ

# 诊断更详细
typst compile -d main.typ
```

### 监听（边写边编）

```bash
typst watch main.typ
typst watch main.typ out/main.pdf --open
```

### 多格式导出

```bash
# PDF（默认）
typst compile main.typ main.pdf

# PNG / SVG（按页；文件名可用 {p}/{0p} 等占位，视版本帮助为准）
typst compile main.typ main.png
typst compile main.typ page-{0p}.png
typst compile main.typ main.svg

# 查看当前 CLI 支持的 format / 子命令
typst help compile
typst --help
```

> 注意：HTML / PDF 标准 / bundle 等能力随版本演进。使用前以 `typst help compile` 为准；本技能 demos 以 PDF 为主。

### 查询文档树（自动化）

```bash
# 查询标题等元素（selector 语法随版本略有差异）
typst query main.typ "<heading>"
typst query main.typ "heading" --field body
typst query main.typ "figure" --one
```

用途：生成目录数据、检查标签、CI 校验结构。

### 字体

```bash
typst fonts
typst fonts --variants
```

### 包与更新

```typ
#import "@preview/example:0.1.0": *
```

```bash
# 部分版本提供 update 子命令
typst update
typst update --force
```

包缓存通常在用户目录下的 Typst 缓存路径；离线环境需预下载。

### 实用组合

```bash
# 开发循环
typst watch main.typ out/main.pdf

# CI 一次性构建
typst compile --root . docs/report.typ dist/report.pdf

# 批量导出预览图
typst compile slides.typ preview-{0p}.png
```

更多速查见：`assets/cli/common-commands.md`

---

## 常见任务配方

### 1) 最小可编译文档

```typ
#set page(paper: "a4")
#set text(size: 11pt)

= Hello Typst
正文从这里开始。
```

参考：`assets/demos/01-hello.typ`

### 2) 学术报告骨架

```typ
#set document(title: "Title", author: "Name")
#set page(paper: "a4", margin: 2.2cm, numbering: "1")
#set heading(numbering: "1.1")
#set par(justify: true)
#set text(font: ("New Computer Modern", "Source Han Serif SC"))

#align(center)[
  #text(16pt, weight: "bold")[报告标题]
  #v(0.6em)
  作者 · 单位 · 日期
]

= 引言
= 方法
= 结果
= 结论
#bibliography("works.bib")
```

参考：`assets/demos/12-advanced-paper.typ`

### 3) 页面与页眉页脚

```typ
#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, x: 2cm),
  header: align(right)[内部报告],
  footer: context align(center)[#counter(page).display("1 / 1", both: true)],
)
```

参考：`assets/demos/04-page-setup.typ`  
指南对应：Page Setup Guide

### 4) 数学

```typ
行内 $Q = rho A v + C$。

独立公式：
$ sum_(i=0)^n (Q_i (a_i - epsilon)) / 2 $

$ v := vec(x_1, x_2, x_3) $
```

参考：`assets/demos/05-math.typ`

### 5) 表格

```typ
#figure(
  table(
    columns: 3,
    align: (left, center, right),
    table.header([项目], [数量], [备注]),
    [冰川 A], [12], [稳定],
    [冰川 B], [7], [退缩],
  ),
  caption: [示例表],
) <tab-demo>
```

参考：`assets/demos/06-table.typ`  
指南对应：Table Guide

### 6) 图与引用

```typ
#figure(
  // 无外部图片时用图形占位
  rect(width: 70%, height: 3cm, fill: luma(92%), stroke: 0.5pt)[
    #align(center + horizon)[示意图]
  ],
  caption: [示例图],
) <fig-demo>

见图 @fig-demo。
```

参考：`assets/demos/07-figure-layout.typ`

### 7) 参考文献

```typ
我们采用 @glacier-melt 的模型。
#bibliography("works.bib", style: "ieee")
```

参考：`assets/demos/10-bibliography.typ` + `assets/data/works.bib`

### 8) 数据导入

```typ
// with: typst compile --root assets assets/demos/09-data-loading.typ
#let rows = csv("/data/sample.csv")
#let conf = json("/data/sample.json")
```

参考：`assets/demos/09-data-loading.typ`

### 9) 可复用模板

`template.typ`：

```typ
#let conf(title: "", authors: (), body) = {
  set document(title: title, author: authors)
  set page(numbering: "1")
  set heading(numbering: "1.1")
  align(center)[#text(16pt, weight: "bold")[#title]]
  body
}
```

`main.typ`：

```typ
#import "template.typ": conf
#show: conf.with(title: "My Paper", authors: ("Ada",))
= Intro
...
```

参考：`assets/demos/11-template/`

### 10) 脚本化内容

```typ
#let notes = ("alpha", "beta", "gamma")
#for n in notes [
  - #n
]
```

参考：`assets/demos/08-scripting.typ`

---

## LaTeX 用户速对照

| LaTeX | Typst |
|-------|-------|
| `\section{}` | `= ` |
| `\textbf{}` / `\emph{}` | `*bold*` / `_emph_` |
| `\begin{itemize}` | `- item` |
| `\begin{enumerate}` | `+ item` |
| `\includegraphics` | `#image("a.png")` |
| `\cite{}` | `@key` |
| `$...$` / `\[...\]` | `$...$`（两侧空格变 display） |
| `\usepackage` | `#import "@preview/..."` |
| 文档类 | 自定义模板函数 + set/show |
| `\newcommand` | `#let name = ...` |

参考：Guide for LaTeX Users；示例见 demos 全文。

---

## 中文排版建议

```typ
#set text(
  font: ("New Computer Modern", "Noto Serif CJK SC", "SimSun"),
  lang: "zh",
  region: "cn",
)
#set par(justify: true, first-line-indent: 2em)
// 标题后首段常取消缩进，可用 show heading 调整
```

若编译报找不到字体：

1. `typst fonts` 查看可用字体名  
2. 换成系统已有字体（Windows 常见：`SimSun`, `Microsoft YaHei`, `KaiTi`）  
3. 或 `--font-path` 指向字体目录

---

## 排错清单

| 现象 | 处理 |
|------|------|
| unknown variable / function | 检查拼写、是否缺 `#`、是否在正确模式 |
| file not found | 检查相对路径；多文件用 `--root` |
| font not found | `typst fonts`；换字体名或 `--font-path` |
| label not found | 确认 `<label>` 与 `@label` 一致且元素可引用 |
| bibliography empty | 确认有引用且 bib 路径正确 |
| package download fail | 网络/代理；离线预缓存包 |
| 中文乱码/方框 | 未设置 CJK 字体 |
| watch 不更新 | 文件未保存；路径不在 root 内 |

编译时始终阅读报错中的 **span/行号**，优先修第一个错误。

---

## 推荐工作流（给 AI）

1. **确认目标**：PDF 报告 / 作业 / 模板 / 公式片段 / CLI 脚本  
2. **选择 demo**：从 `assets/demos/` 复制最接近的起点  
3. **改写内容**：标题、set 规则、章节、图表  
4. **准备数据**：`assets/data/` 风格放置 csv/json/bib/图片  
5. **编译验证**：
   ```bash
   typst compile path/to/main.typ
   ```
6. **按需 watch / query / 导出 PNG**  
7. **交付**：源码 + 编译命令 +（若失败）字体/路径说明

---

## 资产索引

```
assets/
  cli/common-commands.md      # CLI 速查
  data/sample.csv             # CSV 示例
  data/sample.json            # JSON 示例
  data/works.bib              # BibLaTeX 示例
  demos/01-hello.typ
  demos/02-markup-basics.typ
  demos/03-set-show-rules.typ
  demos/04-page-setup.typ
  demos/05-math.typ
  demos/06-table.typ
  demos/07-figure-layout.typ
  demos/08-scripting.typ
  demos/09-data-loading.typ
  demos/10-bibliography.typ
  demos/11-template/template.typ
  demos/11-template/main.typ
  demos/12-advanced-paper.typ
  demos/13-cli-input.typ      # --input 示例
```

### 建议编译命令（在技能根目录）

```bash
# 单文件 demo
typst compile assets/demos/01-hello.typ

# 数据 / 参考文献：必须指定 --root assets（路径以 /data 为根）
typst compile --root assets assets/demos/09-data-loading.typ
typst compile --root assets assets/demos/10-bibliography.typ

# 模板
typst compile assets/demos/11-template/main.typ

# 输入变量
typst compile assets/demos/13-cli-input.typ --input title="Demo" --input author="You"
```

---

## 输出约定

帮助用户写 Typst 时：

1. 给出完整可编译文件内容（或明确的多文件结构）  
2. 附上一条可直接运行的 `typst compile ...`  
3. 如依赖字体/包/数据文件，逐条列出  
4. 复杂版式优先 set/show + 模板函数，避免层层硬编码  
5. 需要图表示意但无资源时，用 `rect`/`circle`/`table`/`cetz`（若可导入）占位  

---

## 参考地图（官方文档结构）

- Tutorial：Writing → Formatting → Advanced Styling → Templates  
- Reference：Syntax / Styling / Scripting / Model / Text / Math / Layout / Visualize / Introspection / Data Loading / PDF·PNG·SVG  
- Guides：LaTeX Users / Page Setup / Table / Accessibility  

本技能不替代完整官方文档，而是把**高频写法 + 可运行样例 + CLI**压缩为可执行工作流。
