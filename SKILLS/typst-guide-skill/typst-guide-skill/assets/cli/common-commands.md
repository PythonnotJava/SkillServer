# Typst CLI 常用命令速查

以本机 `typst help` / `typst help compile` 为准。以下覆盖日常高频用法。

## 全局

```bash
typst --version
typst --help
typst help
typst help compile
typst help watch
typst help query
typst help fonts
```

## compile

```bash
# PDF
typst compile main.typ
typst compile main.typ dist/main.pdf

# 项目根（多文件 / 资源相对路径）
typst compile --root . src/main.typ

# 自定义字体目录
typst compile --font-path ./fonts --font-path "C:/Windows/Fonts" main.typ

# 传入 sys.inputs
typst compile --input mode=draft --input author="Ada" main.typ

# PNG / SVG（多页时注意输出文件名模式，见 help）
typst compile main.typ preview.png
typst compile main.typ page-{0p}.png
typst compile main.typ main.svg

# 诊断
typst compile -d main.typ
```

常用选项（名称可能随版本略有差异）：

| 选项 | 作用 |
|------|------|
| `--root <dir>` | 项目根，限制路径读取范围 |
| `--font-path <dir>` | 额外字体目录（可重复） |
| `--input key=value` | 注入 `sys.inputs` |
| `--format pdf\|png\|svg` | 输出格式（若支持） |
| `-d` / `--diagnostic-format` | 诊断输出相关 |

## watch

```bash
typst watch main.typ
typst watch main.typ out/main.pdf
typst watch --root . src/main.typ out/main.pdf
```

改文件自动重编译，适合本地写作。

## query

```bash
typst query main.typ "heading"
typst query main.typ "<heading>"
typst query main.typ "figure" --field caption
typst query main.typ "heading" --one
```

用于提取标题、图注、自定义 metadata，做检查或生成辅助文件。

## fonts

```bash
typst fonts
typst fonts --variants
```

## update（若 CLI 提供）

```bash
typst update
typst update --force
typst update --list
```

## 推荐脚本片段

### Windows PowerShell

```powershell
typst compile --root . .\main.typ .\out\main.pdf
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

### Bash

```bash
#!/usr/bin/env bash
set -euo pipefail
typst compile --root . main.typ out/main.pdf
```

## 退出码

- `0`：成功
- 非 `0`：语法/路径/字体/包等问题；先读 stderr 第一条错误
