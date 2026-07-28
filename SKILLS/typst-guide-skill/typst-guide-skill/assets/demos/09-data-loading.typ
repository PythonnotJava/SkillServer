// 09-data-loading.typ — CSV / JSON 等数据加载
// 必须从技能包内以 assets 为项目根编译，避免读出 root:
//   typst compile --root assets assets/demos/09-data-loading.typ
// 或在 assets 目录:
//   typst compile --root . demos/09-data-loading.typ

#set page(paper: "a5", margin: 1.3cm)
#set text(size: 10.5pt)
#set heading(numbering: "1.")

= 数据加载

== JSON

#let meta = json("/data/sample.json")

- 标题: *#meta.title*
- 作者: #meta.author
- 版本: #meta.version
- 站点数量: #str(meta.metrics.sites)
- 标签: #meta.tags.join(", ")

== CSV

#let rows = csv("/data/sample.csv")
// 第一行是表头
#let header = rows.first()
#let body = rows.slice(1)

#figure(
  table(
    columns: header.len(),
    align: left,
    stroke: 0.4pt,
    inset: 5pt,
    table.header(..header),
    ..body.flatten(),
  ),
  caption: [从 CSV 导入的观测表],
)

== 说明

Typst 还支持 `yaml` / `toml` / `xml` / `read` / `cbor` 等。
以 `/` 开头的路径相对于 `--root` 项目根，而不是源文件目录。
