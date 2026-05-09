# 数值问题诊断与修复指南

Gurobi 基于**双精度浮点**算术运算，结果只能满足容差级别的可行性和最优性。病态模型会严重拖慢求解甚至给出错误答案。

## 良好模型的系数范围

**推荐**：约束矩阵、目标、边界、右端的系数都在 **`[1e-3, 1e6]`** 之间，**非零之比不超过 `1e9`**。

**典型问题**：
| 现象 | 警告阈值 |
|------|----------|
| 矩阵系数 | `> 1e9` 或 `< 1e-9` |
| 边界 | `\|bound\|> 1e9` |
| 右端 | `\|rhs\| > 1e9` |
| 目标系数 | 相对差距 > `1e9` |
| 条件数 (`KappaExact`) | `> 1e10` 可能有麻烦 |

检查方法：
```python
m.printStats()           # 打印各范围
kappa = m.KappaExact     # 精确条件数
print(f"Condition number: {kappa:.2e}")
```

## 典型症状与根因

### 1. "Warning: variable x has infinite upper bound"
**原因**：未限定变量边界导致大 M 隐式出现。
**修复**：用指示约束替换大 M，或显式设置合理上界。

### 2. "Scaling matrix row/col"
**原因**：矩阵行列尺度悬殊。
**修复**：手动缩放变量或约束（除以典型值），或设 `ScaleFlag=2`。

### 3. 整数微违反 (Trickle Flow)
**现象**：二进制变量值 `0.99999`，导致流量约束被"绕过"。
**修复**：
```python
m.Params.IntegralityFocus = 1   # ~5-10% 性能代价，但消除微违反
```

### 4. 报告最优但解明显错误
**原因**：模型病态 + 容差宽松。
**修复**：
```python
m.Params.NumericFocus = 3
# 检查解的真实违反：
m.Params.OptimalityTarget = 2   # 或用 m.printQuality()
m.printQuality()
```

### 5. 单纯形在可行/不可行之间振荡
**原因**：条件数 > `1e10`。
**修复**：重新缩放模型；`Quad=1` 强制四倍精度（慢）；`Method=2` 内点法通常更稳。

### 6. 内点法诊断不可行/无界失败
**修复**：`BarHomogeneous=1`（齐次 barrier）。

## Big-M 的替代品

**问题**：大 M 约束 `x <= M*y`（`y` 二进制）在 `M` 大时会导致：
- LP 松弛弱 → 根节点下界差
- 整数微违反 → 错误答案
- 条件数激增

**解决方案**（按优先级）：

1. **Indicator constraint**（最推荐）：
   ```python
   m.addConstr((y == 1) >> (x <= ub))
   # Gurobi 会自动尝试 big-M 重构，但大 M 太大时保留作为 indicator
   m.Params.PreSOS1BigM = 1e6   # 控制自动 bigM 阈值
   ```

2. **SOS1 constraint**：变量集合中至多一个非零。

3. **值域切换**：如果 `x` 的实际范围是 `[0, 100]`，用 `M=100` 而不是 `M=1e8`。

4. **单调变换**：如果 `y=1` 强制 `x=0`，另外 `x>=0`，则 `x <= 100*y` 即可，不需要 `1e8 * y`。

## 缩放策略

### 目标缩放

```python
m.Params.ObjScale = -1     # 自动（除以最大系数）
m.Params.ObjScale = 100    # 手动：除以 100
m.Params.ObjScale = -0.5   # 除以最大的 0.5 次方
```

注意：目标缩放会影响对偶变量的尺度。

### 模型缩放

```python
m.Params.ScaleFlag = -1   # 自动（默认）
m.Params.ScaleFlag = 0    # 关闭缩放（有时缓解对原模型的违反）
m.Params.ScaleFlag = 1    # 标准缩放
m.Params.ScaleFlag = 2    # 激进（对几何均值）
m.Params.ScaleFlag = 3    # 更激进
```

## NumericFocus 级别

| 值 | 行为 | 适用 |
|----|------|------|
| 0（默认） | 速度优先 | 良好模型 |
| 1 | 更小心选主元 | 轻度病态 |
| 2 | 单纯形四倍精度，barrier 额外修正 | 中度病态 |
| 3 | 最保守 | 严重病态，接受 2-5 倍慢 |

## 数值问题 Checklist

求解前：
1. `m.printStats()` 看系数范围是否合理
2. 检查 `m.KappaExact`

求解后如果怀疑数值问题：
1. `m.printQuality()` — 查原始/对偶/整数违反
2. 若违反 > 容差，调高 `NumericFocus`
3. 若单纯形振荡，改 `Method=1` 或 `2`
4. 若 barrier 失败，加 `BarHomogeneous=1`
5. 若整数违反，`IntegralityFocus=1`

## 实战：找到"坏"系数

```python
# 找绝对值最大/最小的非零系数
coefs = []
for c in m.getConstrs():
    row = m.getRow(c)
    for i in range(row.size()):
        coef = row.getCoeff(i)
        coefs.append((abs(coef), c.ConstrName, row.getVar(i).VarName))
coefs.sort(reverse=True)
print("最大:", coefs[:5])
print("最小非零:", [x for x in coefs if x[0] > 0][-5:])
```

找到不合理的值后**重新建模**——这比任何参数调整都有效。

## 稀疏系数的陷阱

`x = 1e-10` 等的"稀疏非零"在预处理中会被当作零去掉，改变模型语义。对于真的想表达"小权重"的场景，要么合理缩放到 `1e-3` 以上，要么用别的建模方式。

## 条件数太大的本质

模型的 `KappaExact` 反映了"系数矩阵求逆的数值误差放大倍数"。`1e10` 意味着单位舍入误差（`1e-16`）会被放大到 `1e-6`，等于默认容差——任何求解结果都"看起来"可行但实际可能不是。

真正的修复是**重新建模**：
- 缩放变量单位（秒 → 小时）
- 重新参数化（`x` → `x/1000`）
- 删除冗余约束
- 避免 `a*x - a*y <= 0` 这种数值上等价于 `x <= y` 的写法
