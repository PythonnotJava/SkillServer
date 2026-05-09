# 不可行性 / 无界性 诊断

模型求解返回 `INFEASIBLE` / `UNBOUNDED` / `INF_OR_UNBD` 时，Gurobi 提供一套工具定位问题。

## 状态区分

- `INFEASIBLE`：模型确实不可行
- `UNBOUNDED`：模型无界
- `INF_OR_UNBD`：求解器无法区分（常因为预处理）。用以下代码重新求解：
  ```python
  m.Params.DualReductions = 0
  m.optimize()
  # 现在状态会精确为 3 或 5
  ```

## 工具 1: IIS（不可约不一致子系统）

IIS = 最小的约束/边界子集，使它们冲突而无法同时满足。移除任一个即变可行。

```python
m.computeIIS()
m.write("model.ilp")   # 写出 IIS（类 LP 格式）

# 或程序化地检查
for c in m.getConstrs():
    if c.IISConstr:
        print(f"IIS constraint: {c.ConstrName}")
for v in m.getVars():
    if v.IISLB:
        print(f"IIS lower bound on {v.VarName}")
    if v.IISUB:
        print(f"IIS upper bound on {v.VarName}")
```

**注意**：
- 一个模型可能有**多个 IIS**，Gurobi 只找其中一个（不一定最小）
- MIP 的 IIS 在**线性松弛**上计算
- 控制算法：`IISMethod`（0=默认，1=限制性，2=速度优先）

### `IISConstrForce` / `IISLBForce` / `IISUBForce`

强制/排除某些约束从 IIS 算法中：
- `1`：强制包含
- `-1`：强制排除
- `0`：算法自选（默认）

## 工具 2: feasRelax（可行松弛）

把所有"硬"约束变为带惩罚的"软"约束，找出最小违反量的解。

```python
# feasRelaxS(relaxobjtype, minrelax, vrelax, crelax)
m.feasRelaxS(
    relaxobjtype=0,   # 0=sum|violation|, 1=sum(violation²), 2=count
    minrelax=False,   # True 则先最小化总违反，再在此基础上求原目标
    vrelax=True,      # 松弛变量边界
    crelax=True       # 松弛约束
)
m.optimize()

# 检查哪些约束被违反
for c in m.getConstrs():
    # feasRelax 会为每个软约束加一个 ArtP/ArtN 变量
    # 通过 c.Slack 或新增变量查
    pass
```

更精细控制（按约束单独设惩罚）：

```python
m.feasRelax(
    relaxobjtype=0,
    minrelax=True,
    vars=[x, y],       # 只松弛这些变量的边界
    lbpen=[1.0, 2.0],  # 对应下界违反的惩罚
    ubpen=[1.0, 2.0],
    constrs=[c1, c2],
    rhspen=[10.0, 5.0]
)
```

### relaxobjtype

- `0`：`sum(violations)` — 线性（最快）
- `1`：`sum(violations²)` — 二次（QP，对大违反敏感）
- `2`：`count(violations > 0)` — 整数（选最少约束违反的解，慢）

## 工具 3: Farkas 不可行证明（LP）

对不可行 LP，`FarkasDual` 属性给出不可行性的**证明向量**：

```python
m.Params.InfUnbdInfo = 1
m.optimize()
if m.Status == GRB.INFEASIBLE:
    for c in m.getConstrs():
        if abs(c.FarkasDual) > 1e-6:
            print(f"{c.ConstrName}: FarkasDual = {c.FarkasDual}")
    # 同时 c.FarkasProof 给出证明值
```

## 工具 4: 无界射线 (UnbdRay)

对无界 LP：

```python
m.Params.InfUnbdInfo = 1
m.optimize()
if m.Status == GRB.UNBOUNDED:
    for v in m.getVars():
        if abs(v.UnbdRay) > 1e-9:
            print(f"{v.VarName} 沿方向 {v.UnbdRay} 可无限改进")
```

## 常见不可行原因

1. **边界冲突**：`x >= 10, x <= 5`
2. **资源不足**：需求总量 > 供给总量
3. **逻辑约束互斥**：`A => B` 和 `A, not B` 同时存在
4. **罗兰 / 大 M 太小**：模型要求 `y=1 => x>=100`，但 `x.UB=50`
5. **数值误差**：容差边缘的约束被求解器判为不可行
6. **整数可行性**：LP 松弛可行但无整数解——不同于 LP 不可行

## 常见无界原因

1. **遗漏上界**：默认 `ub=+inf`，与目标方向配合导致无界
2. **遗漏下界**：如果定义 `x` 为自由变量但本应 `>= 0`
3. **错误符号**：`max c*x` 而 `c` 全负且 `x >= 0`

## 诊断流程

```python
m.optimize()

if m.Status == GRB.INFEASIBLE:
    # 1. 先 IIS 找冲突源
    m.computeIIS()
    m.write("infeas.ilp")

    # 2. 如果 IIS 太大，用 feasRelax 查看"最便宜"的修复
    m.feasRelaxS(0, True, True, True)
    m.optimize()
    # 看哪些 ArtP_*/ArtN_* 变量非零

elif m.Status == GRB.INF_OR_UNBD:
    m.Params.DualReductions = 0
    m.optimize()

elif m.Status == GRB.UNBOUNDED:
    m.Params.InfUnbdInfo = 1
    m.optimize()
    # 查 UnbdRay

elif m.Status == GRB.NUMERIC:
    m.Params.NumericFocus = 3
    m.optimize()
```

## 预防性建议

- 每个变量都设合理 `lb/ub`（避免意外无界）
- 避免大 M（用 indicator constraints）
- 开发阶段用 `m.printStats()` 检查系数范围
- 大模型分模块逐步构建，每步先可行再加难约束
- 引入 slack 变量 + 大惩罚 = 软约束（类似 feasRelax 但可微调）：
  ```python
  slack = m.addVar(lb=0, name="slack_demand")
  m.addConstr(supply_expr >= demand - slack)
  # 在目标里加上大惩罚
  m.setObjective(original_obj + 1e6 * slack, GRB.MINIMIZE)
  ```
