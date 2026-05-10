# 非线性建模指南

Gurobi 13.0 支持**三种非线性建模方式**，推荐优先级从高到低：

## 1. Nonlinear Constraints (13.0 推荐)

**复合多元非线性表达式**。Python 中通过 `nlfunc` 辅助函数或表达式算术构造 `NLExpr`。

```python
import gurobipy as gp
from gurobipy import GRB, nlfunc

m = gp.Model()
x = m.addVar(lb=-5, ub=5, name="x")
y = m.addVar(lb=-5, ub=5, name="y")
z = m.addVar(lb=-GRB.INFINITY, name="z")

# z = x^2 + sin(x*y) + exp(-0.5*y)
m.addConstr(z == x*x + nlfunc.sin(x*y) + nlfunc.exp(-0.5*y))

# 不等式也可以
m.addConstr(z >= nlfunc.log(x + 2))
```

### nlfunc 支持的操作

| 操作 | 用法 | 备注 |
|------|------|------|
| 算术 | `+`, `-`, `*`, `/`, `**` | 操作数可以是 Var / LinExpr / NLExpr / 常数 |
| 幂 | `x**a`, `nlfunc.pow(x, a)` | |
| 平方/开方 | `x*x`, `nlfunc.sqrt(x)` | |
| 指数 | `nlfunc.exp(x)` | 自然指数 |
| 对数 | `nlfunc.log(x)`, `nlfunc.log2(x)`, `nlfunc.log10(x)` | |
| 三角 | `nlfunc.sin(x)`, `cos(x)`, `tan(x)` | |
| 双曲 | `nlfunc.tanh(x)` | **13.0 新** |
| 逻辑 | `nlfunc.logistic(x) = 1/(1+exp(-x))` | |
| 符号幂 | `nlfunc.signpow(x, a)` | **13.0 新**；= `sign(x)·|x|^a`, `a ≥ 1` |

### 控制求解策略

- 默认：**空间分支定界** — 求**全局最优**（但可能慢）
- 属性 `FuncNonlinear=0` 或全局参数 `FuncNonlinear=0`：改为**静态分段线性近似**
- 精度参数：`FuncPieces`, `FuncPieceLength`, `FuncPieceRatio`, `FuncPieceError`, `FuncMaxVal`

```python
m.Params.FuncNonlinear = 1   # 全局用空间 B&B（默认）
# 或对单个约束 c.FuncNonlinear = 0 改为 PWL
```

## 2. NL Barrier（13.0 预览）— 局部最优

如果你**只需要局部最优**（NLP 没有离散元素，全局求解太慢），设：

```python
m.Params.OptimalityTarget = 1   # 启用 NL barrier
m.Params.NLBarIterLimit = 500
m.optimize()
# Status 将是 LOCALLY_OPTIMAL (18) 或 LOCALLY_INFEASIBLE (19)
```

**何时使用**：
- 全部连续变量
- 含非线性约束（但没有整数、SOS、PWL）
- 大规模（数千变量以上）
- 可以接受局部解

## 3. Function Constraints（已弃用）

**不要**使用以下 API（13.0 起发出弃用警告，未来删除）：
- `addGenConstrExp` / `addGenConstrLog` / `addGenConstrPow`
- `addGenConstrSin` / `Cos` / `Tan` / `Logistic` / `Poly` / `ExpA` / `LogA`
- 以及相关属性 `FuncPieceError/Length/Ratio/Pieces/Nonlinear`（这些属性现在属于非线性约束）

替换模式：

| 旧 (deprecated) | 新 (13.0) |
|-----------------|-----------|
| `m.addGenConstrExp(x, y)` | `m.addConstr(y == nlfunc.exp(x))` |
| `m.addGenConstrLog(x, y)` | `m.addConstr(y == nlfunc.log(x))` |
| `m.addGenConstrPow(x, y, a)` | `m.addConstr(y == nlfunc.pow(x, a))` |
| `m.addGenConstrSin(x, y)` | `m.addConstr(y == nlfunc.sin(x))` |
| `m.addGenConstrLogistic(x, y)` | `m.addConstr(y == nlfunc.logistic(x))` |

## 4. Piecewise-Linear (PWL) 建模

若你的非线性函数确定是**单变量**且可以手动分段线性化，用 `addGenConstrPWL` 可能更快：

```python
# 定义分段点
xpts = [-5, -2, 0, 2, 5]
ypts = [25, 4, 0, 4, 25]   # y = x²
m.addGenConstrPWL(x, y, xpts, ypts)
```

这在 **不**追求全局精确、希望解得更快时非常有效。注意：
- 引入 PWL 会把模型转为 MIP
- 相邻点斜率递增 → 凸分段（可单独高效求解）
- 否则 Gurobi 引入二进制变量

## 5. 其他 API（C/C++/Java/.NET）中的非线性

这些 API 没有 Python `nlfunc` 的便捷语法，需要手动构造**表达式树**：

### C API 示例

```c
/* 表达式树：y = exp(x) + sin(x) */
int opcode[] = {
    GRB_OPCODE_PLUS,
    GRB_OPCODE_EXP,
    GRB_OPCODE_VARIABLE,
    GRB_OPCODE_SIN,
    GRB_OPCODE_VARIABLE
};
double data[] = {0, 0, (double)x_idx, 0, (double)x_idx};
int parent[] = {-1, 0, 1, 0, 3};

GRBaddgenconstrNL(model, "nl1", y_idx, 5, opcode, data, parent);
```

详见 C API 参考手册 `GRBaddgenconstrNL` / `GRBgetgenconstrNL`。

### C++ / Java / .NET 相似。

## 完整示例：非线性回归

拟合 `y = a * exp(b*x) + c` 到数据点 `(xi, yi)`，最小化平方误差：

```python
import gurobipy as gp
from gurobipy import GRB, nlfunc

xs = [0.0, 0.5, 1.0, 1.5, 2.0]
ys = [1.0, 1.6, 2.7, 4.5, 7.4]
n = len(xs)

m = gp.Model()
a = m.addVar(lb=0.1, ub=10, name="a")
b = m.addVar(lb=-2, ub=2, name="b")
c = m.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name="c")

# 残差变量
r = m.addVars(n, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="r")
for i in range(n):
    m.addConstr(r[i] == a * nlfunc.exp(b * xs[i]) + c - ys[i])

# 目标：min sum r_i^2
m.setObjective(gp.quicksum(r[i]*r[i] for i in range(n)), GRB.MINIMIZE)

# 局部最优即可
m.Params.OptimalityTarget = 1
m.optimize()

print(f"a={a.X:.3f} b={b.X:.3f} c={c.X:.3f}")
```

## 常见陷阱

1. **定义域**：`log(x)` 需 `x > 0`，`sqrt(x)` 需 `x >= 0`，`1/x` 需 `x != 0`。这些由**变量的 lb/ub** 保证；否则 Gurobi 报错或给出意外结果。

2. **非线性目标需引入辅助变量**：Gurobi 的目标只能是**线性 / 二次 / 分段线性 / 多目标线性**。非线性目标：
   ```python
   aux = m.addVar(lb=-GRB.INFINITY, name="aux")
   m.addConstr(aux == nlfunc.exp(x) + nlfunc.sin(y))
   m.setObjective(aux, GRB.MINIMIZE)
   ```

3. **`x**a` 与 `nlfunc.pow(x, a)`**：`a` 为整数时优先用 `x*x*...` 或 quadratic；`a` 为分数或 `x` 可能为负时必须用 `signpow`。

4. **求解时间**：空间分支定界对非线性约束**很慢**。如果只需要 feasible solution，考虑：
   - `FuncNonlinear=0`（PWL 近似）
   - `NonConvex=2` + 二次重构
   - `OptimalityTarget=1`（NL barrier 局部最优）

5. **与整数结合**：非线性约束 + 整数变量 = MINLP，最难的一类。小规模可接受，大规模很可能超时。

## 快速决策树

```
问题全线性？ → LP / MIP
 ↓ 否
非线性全凸？ → QP / QCP，barrier 即可
 ↓ 否
可以局部最优？ → NL Barrier (OptimalityTarget=1)
 ↓ 否
含离散元素？ → 全局空间 B&B (默认)，或 PWL 近似 (FuncNonlinear=0)
```
