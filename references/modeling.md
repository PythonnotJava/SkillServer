# Gurobi 建模组件详解

Gurobi 模型由**变量 (Variables)**、**约束 (Constraints)** 和 **目标 (Objective)** 构成。本文详解每类对象的选择、语法和陷阱。

## 1. 变量 (Variables)

### 变量类型

| 类型 | 常量 | 含义 |
|------|------|------|
| 连续 | `GRB.CONTINUOUS` | 任意实数（默认非负）。一般实数需显式设 `lb=-GRB.INFINITY` |
| 整数 | `GRB.INTEGER` | 整数值，满足 `IntFeasTol` 容差 |
| 二进制 | `GRB.BINARY` | 仅取 0 或 1，边界等效 `[0,1]` + 整数 |
| 半连续 | `GRB.SEMICONT` | 取 0 或 `[lb, ub]` 内值 |
| 半整数 | `GRB.SEMIINT` | 取 0 或 `[lb, ub]` 内整数 |

### 边界

- 默认 `lb=0.0`, `ub=GRB.INFINITY`。
- 自由变量（无上下界）设 `lb=-GRB.INFINITY`。
- 任何 `|bound| > 1e30` 被 Gurobi 视为无穷大。
- 变量解允许小幅违反边界，容差由 **`FeasibilityTol`** 控制（默认 1e-6）。

### Python API 创建变量

```python
import gurobipy as gp
from gurobipy import GRB

m = gp.Model()

# 单个变量
x = m.addVar(lb=0, ub=10, vtype=GRB.CONTINUOUS, name="x")

# 一维批量
vars1 = m.addVars(n, vtype=GRB.BINARY, name="v")  # v[0]..v[n-1]

# 多维字典形式（返回 tupledict）
x = m.addVars([(i,j) for i in I for j in J],
              lb=0, ub=cap, obj=cost, vtype=GRB.CONTINUOUS, name="x")
# 访问：x[i,j]   切片求和：x.sum(i, '*')

# MVar (matrix variable) — 矩阵运算风格
X = m.addMVar((m_rows, n_cols), vtype=GRB.CONTINUOUS, name="X")
```

## 2. 约束 (Constraints)

Gurobi 只支持 `<=`、`>=`、`==`，不支持严格不等号或 `!=`。

### 2.1 线性约束

```python
m.addConstr(3*x + 4*y <= 5*z, name="c1")
m.addConstrs((x[i] + y[i] == 1 for i in I), name="c")
m.addConstrs((quicksum(x[i,j] for j in J) <= capacity[i] for i in I), name="cap")
```

**范围约束**（range constraint）：`lhs <= expr <= rhs`：

```python
m.addRange(3*x + 4*y, 2, 10, name="range")
```

### 2.2 SOS (Special Ordered Set)

- **SOS1**：变量列表中至多一个可非零。
- **SOS2**：变量列表中至多两个可非零，且两个必须在有序列表中相邻。

```python
m.addSOS(GRB.SOS_TYPE1, [x, y, z], [1, 2, 3])  # 权重仅用于排序
```

### 2.3 二次约束

```python
m.addConstr(x*x + y*y <= 1, name="unit_disk")  # 凸（PSD）
m.addConstr(x*y + 2*z*z <= 5, name="nonconvex")  # 非凸需 NonConvex=2
```

**凸性识别**（Gurobi 自动识别为凸的形式）：
- `x' Q x + q' x <= b`，其中 `Q` PSD
- `x' Q x <= y²`，`Q` PSD，`y >= 0`（二阶锥）
- `x' Q x <= y*z`，`Q` PSD，`y,z >= 0`（旋转二阶锥）

设 `m.Params.NonConvex = 2` 接受任意二次约束（空间分支定界，慢很多）。

### 2.4 一般约束 (General Constraints)

Gurobi 提供高阶约束，自动翻译为底层 MIP 表述：

```python
# MAX / MIN / ABS
m.addGenConstrMax(r, [x1, x2, x3], constant=0)
m.addGenConstrMin(r, [x1, x2, x3])
m.addGenConstrAbs(r, x)

# 逻辑 AND / OR（要求二进制变量）
m.addGenConstrAnd(r, [b1, b2, b3])
m.addGenConstrOr(r, [b1, b2])

# Norm 约束 (0/1/2/inf 范数)
m.addGenConstrNorm(r, [x, y, z], which=2)  # r = ||·||_2

# Indicator constraint: if b==1 then expr <= rhs
m.addGenConstrIndicator(b, True, x + y <= 3)
# 语法糖等价
m.addConstr((b == 1) >> (x + y <= 3))

# Piecewise-linear: y = f(x) 由分段点定义
m.addGenConstrPWL(x, y, xpts, ypts)
```

### 2.5 非线性约束 (Nonlinear Constraints, 13.0 推荐)

**重要**：Gurobi 13.0 起 **Function Constraints** (`addGenConstrExp/Log/Pow/Sin/Cos/Tan/Logistic/Poly`) 已**弃用**。推荐用 **Nonlinear Constraints**。

Python 中用 `gurobipy.nlfunc` 辅助函数构造非线性表达式（`NLExpr`）：

```python
import gurobipy as gp
from gurobipy import GRB, nlfunc

m = gp.Model()
x = m.addVar(lb=0.1, ub=10, name="x")
y = m.addVar(lb=-GRB.INFINITY, name="y")

# y = exp(x) + log(x)  （非线性等式）
m.addConstr(y == nlfunc.exp(x) + nlfunc.log(x))

# y >= sin(x) * cos(x)
m.addConstr(y >= nlfunc.sin(x) * nlfunc.cos(x))

# signpow: signpow(x, a) = sign(x) * |x|^a  （13.0 新增）
m.addConstr(y == nlfunc.signpow(x, 2))

# tanh（13.0 新增）
m.addConstr(y == nlfunc.tanh(x))
```

其他 API（C/Java/.NET）要用 **表达式树** 手动构造（`OPCODE_PLUS`/`OPCODE_EXP` 等），较繁琐。

**关键参数**：
- `FuncNonlinear` 或 `GenConstrNL` 属性控制处理方式：
  - `1`（默认）：空间分支定界（可证明全局最优）
  - `0`：静态分段线性近似（更快但近似）
- `FuncPieces`, `FuncPieceLength`, `FuncPieceRatio`, `FuncPieceError` 控制分段线性近似的精度。

### 支持的一元非线性操作（OPCODE 表）

| 操作 | OPCODE |
|------|--------|
| 加 / 减 / 乘 / 除 | PLUS / MINUS / MULTIPLY / DIVIDE |
| 一元负号 | UMINUS |
| 平方 / 平方根 | SQUARE / SQRT |
| exp / log / log2 / log10 | EXP / LOG / LOG2 / LOG10 |
| pow(u,v) | POW |
| sin / cos / tan | SIN / COS / TAN |
| logistic: 1/(1+e^-x) | LOGISTIC |
| tanh（13.0 新） | TANH |
| signpow(x,a): sign(x)·\|x\|^a（13.0 新） | SIGNPOW |

## 3. 目标 (Objective)

### 3.1 线性目标

```python
# 方式 1：通过 Var 的 Obj 属性
x = m.addVar(obj=3.0, name="x")

# 方式 2：setObjective
m.setObjective(3*x + 4*y - z, GRB.MINIMIZE)
m.setObjective(gp.quicksum(c[i]*x[i] for i in I), GRB.MAXIMIZE)

# 模型总体方向（覆盖 ModelSense）
m.ModelSense = GRB.MINIMIZE  # 或 GRB.MAXIMIZE
```

### 3.2 分段线性目标

```python
# 对单个变量 x 指定分段线性目标 f(x)
m.setPWLObj(x, xpts=[1, 3, 5], ypts=[1, 2, 4])
```

凸分段线性目标有专用快速单纯形算法。非凸分段线性目标会把问题变为 MIP。

### 3.3 二次目标

```python
m.setObjective(3*x*x + 4*y*y + 2*x*y + x, GRB.MINIMIZE)
```

- 凸二次 + 线性约束 + 连续变量 → QP，单纯形或内点法均可
- 凸二次 + 离散 → MIQP（根节点必须用单纯形）
- 非凸二次 → 设 `NonConvex=2`

### 3.4 多目标

Gurobi 只支持多个**线性**目标，分层（hierarchical）或加权混合（blended）：

```python
m.NumObj = 2
# 第 0 个：主目标
m.setObjectiveN(cost_expr, index=0, priority=2, name="cost")
# 第 1 个：次目标
m.setObjectiveN(time_expr, index=1, priority=1, name="time")
```

详见 `multi-objective.md`。

## 4. 容差与条件良好性

- **`FeasibilityTol`**（默认 `1e-6`）：原始约束违反容差
- **`IntFeasTol`**（默认 `1e-5`）：整数可行性违反
- **`OptimalityTol`**（默认 `1e-6`）：对偶约束违反
- **`MIPGap`**（默认 `1e-4`）：MIP 相对最优性差距
- **`MIPGapAbs`**：绝对差距

**不要**把容差调得比系数值的相对精度还小——这会导致求解器"振荡"。详见 `numerical-issues.md`。
