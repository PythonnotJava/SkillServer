# 建模技巧大全（中文版精华）

本文汇集了常用的**模型转换技巧**，帮助把自然语言描述的约束转换为数学规划求解器可直接求解的形式。Gurobi 只支持 `<=`、`>=`、`==` 三种关系，所有其他关系都需要转换。

## 1. 关系符号转换

### 1.1 `>` 和 `<` 严格不等

**不能直接建模**。对整数变量引入一个"足够小的正数" ε（整数取 1）：

```
x > y  等价于  x >= y + 1   (x, y 整数时)
x > y  等价于  x >= y + ε   (x, y 连续时，ε > 0 但须小心数值问题)
```

### 1.2 `≠` 不等

典型做法：用绝对值转换。以 `x + y ≠ 0` 为例，`x, y` 均为整数：

```
x + y ≠ 0
 ⇔ x + y >= 1  或  x + y <= -1
 ⇔ |x + y| >= 1
```

引入辅助变量：
```python
u = m.addVar(lb=-GRB.INFINITY, vtype=GRB.INTEGER, name="u")
u_abs = m.addVar(lb=0, name="u_abs")
m.addConstr(u == x + y)
m.addGenConstrAbs(u_abs, u)   # u_abs = |u|
m.addConstr(u_abs >= 1)
```

**注意**：Gurobi 10.0 及以下 `addGenConstrAbs` 只支持单变量；更高版本依然建议先引入辅助变量 `u` 再取绝对值，更直观。

## 2. 指示 (Indicator) 约束建模

### 2.1 `z = 1 ⇒ expr 关系`

最推荐方式：
```python
m.addGenConstrIndicator(z, True, x + y <= 10)
# 或语法糖
m.addConstr((z == 1) >> (x + y <= 10))
```

### 2.2 逆否命题 ⇔ 等价转换

常见需求："若 w > 0 则 b = 1"。利用**逆否命题**：
```
w > 0 ⇒ b = 1
 ⇔
b = 0 ⇒ w <= 0   (更易建模)
```

两个方向都建模即可表达双向关系。

### 2.3 经典 Big-M 模式

要表达"`b = 1 ⇒ w >= 1`"：
```
1 - w - M(1 - b) <= 0         (当 b=1 时 1 - w <= 0 即 w >= 1；b=0 时松弛)
```

M 可取 `1 - w` 的一个上界（这里 `M = 1` 足够紧）。

要表达"`b = 0 ⇒ w = 0`"（要求 `w >= 0`）：
```
w <= M*b                       (b=0 时 w <= 0 → w = 0；b=1 时 w <= M)
```

### 2.4 e > 0 ⇔ z = 1 的双向刻画（生产计划缺货典型）

当 `e` 为非负整数变量，z 为 0-1 指示变量表示"`e > 0`"（即 `e >= 1`）：

引入大 M，添加 4 条约束即可双向刻画：
```
e - M·z <= 0                  (z=0 ⇒ e<=0；z=1 松弛)
-(e-1) - M·(1-z) <= 0         (z=1 ⇒ e>=1；z=0 松弛)
L - e - M·(1-z) <= 0          (z=1 ⇒ L<=e)
e - L - M·(1-z) <= 0          (z=1 ⇒ L>=e)
```
最终：`z=1 ⇔ e>=1`，并且 `z=1 ⇒ L=e`，`z=0 ⇒ L=0`（配合 `L >= 0`）。

## 3. Big-M 取值策略

**原则**：M 越紧越好（LP 松弛越紧、收敛越快、数值更稳）。

| 约束模式 | 合理的 M |
|----------|----------|
| `x <= M·y` | `x` 的实际上界（不是 `1e8`） |
| `expr <= rhs + M·(1-z)` | `expr - rhs` 的上界 |
| `lw=1 ⇒ w>=1`，`w` 是天产量 | `M = 1 - 0 = 1` |
| `x >= L - M·(1-z)` | `L - x_min` |

**实战技巧**：若有多个 M 相同的约束，可分别赋不同的 M 值（取该约束语义的紧上界）。例如 `M_i = d_i`（第 i 天需求）比 `M = max_i d_i` 紧得多。

## 4. 分式约束的线性化

### 4.1 乘因子消除除号

对 `a/(b+c) + b/(a+c) + c/(a+b) = 4`，**两边同乘** `(b+c)(a+c)(a+b)`：

得到多项式约束：
```
a(a+c)(a+b) + b(b+c)(a+b) + c(b+c)(a+c) = 4(b+c)(a+c)(a+b)
```
展开后是三次多项式。Gurobi 目前只支持二次约束（MIQCP），需要进一步降阶。

### 4.2 引入辅助变量降阶

对三次项 `x₁·x₂·x₃`，引入 `u = x₁·x₂`，得到两个二次约束：
```python
u = m.addVar(name="u")
w = m.addVar(name="w")
m.addConstr(u == x1 * x2)      # 二次
m.addConstr(w == u * x3)       # 二次
# 现在 w = x1*x2*x3
```

任何 k 次多项式都可通过逐步引入辅助变量降到若干个二次约束（**Reformulation-Linearization Technique**）。

### 4.3 引入中间变量直接表达

更简单的路线 —— 引入 `m_1 = x_1/(x_2+x_3)`：
```python
m1 = m.addVar(lb=0, name="m1")
m.addConstr(x1 == m1 * (x2 + x3))   # 二次约束
```

然后 `m_1 + m_2 + m_3 = 4`（线性）即可。
这种方式引入的是 MIQCP，Gurobi 可以求解。

**注意**：分式约束线性化后**可能引入数值问题**。Gurobi 判断"可行"时有 `1e-6` 容差，对病态模型可能返回违反量 `1e-6` 的"假可行解"。验证方法：代回原分式计算，若残差远大于 `1e-6`，需要**收紧容差**或用不同转换。

## 5. 绝对值约束

### 5.1 `|x|` 的建模

Gurobi 提供原生支持：
```python
x_abs = m.addVar(lb=0, name="x_abs")
m.addGenConstrAbs(x_abs, x)   # x_abs = |x|
```

等价展开（手动）：
```python
x_abs >= x
x_abs >= -x
# 注意：单独这两条只能保证 x_abs 是 |x| 的上界
# 若目标最小化 x_abs，则自然等于 |x|
# 若不是，需加 indicator: x >= 0 ⇒ x_abs = x; x <= 0 ⇒ x_abs = -x
```

### 5.2 `|x + y|` 等复合表达式

`addGenConstrAbs` 在低版本只支持单个变量。通用做法：
```python
u = m.addVar(lb=-GRB.INFINITY, name="u")
u_abs = m.addVar(lb=0, name="u_abs")
m.addConstr(u == x + y)
m.addGenConstrAbs(u_abs, u)
```

### 5.3 `|x| ≥ 1` 的破坏凸性

`|x| >= 1` ⇔ `x >= 1` ∨ `x <= -1`，这是**非凸**。必须引入 0-1 变量或使用 SOS1：

```python
# 方法 1：二进制切换
b = m.addVar(vtype=GRB.BINARY)
M = 100   # x 的绝对值上界
m.addConstr(x >= 1 - M*(1-b))   # b=1: x>=1; b=0: 松弛
m.addConstr(x <= -1 + M*b)      # b=0: x<=-1; b=1: 松弛

# 方法 2：直接对 |x| 建模并要求 >= 1
x_abs = m.addVar(lb=0, name="x_abs")
m.addGenConstrAbs(x_abs, x)
m.addConstr(x_abs >= 1)   # x_abs 本身是凸的，约束 |x|>=1 就变为凸包络的松弛
```

**警告**：方法 2 实际上不严格 —— `x_abs >= x, x_abs >= -x, x_abs >= 1` 允许 `x=0, x_abs=1`。`addGenConstrAbs` 会自动补全 disjunction，所以方法 2 实际等价方法 1。

## 6. max / min 建模

```python
# r = max(x1, x2, x3, constant)
m.addGenConstrMax(r, [x1, x2, x3], constant=5.0)

# r = min(x1, x2, x3)
m.addGenConstrMin(r, [x1, x2, x3])
```

手动展开（当需要传统 MIP 表述时）：

`r = max(x₁, x₂)` 等价于：
```
r >= x1, r >= x2
r <= x1 + M(1-z1)
r <= x2 + M(1-z2)
z1 + z2 >= 1    (至少一个等号成立)
```

## 7. 逻辑 And/Or

```python
# r = 1 ⇔ x1 = x2 = x3 = 1
m.addGenConstrAnd(r, [x1, x2, x3])
# 等价于：
#   r <= x_i  for all i
#   r >= x1 + x2 + x3 - 2

# r = 1 ⇔ x1 = 1 ∨ x2 = 1 ∨ x3 = 1
m.addGenConstrOr(r, [x1, x2, x3])
# 等价于：
#   r >= x_i  for all i
#   r <= x1 + x2 + x3
```

### 乘积线性化 `w = x * y`（二进制 × 连续 或 二进制 × 二进制）

**二进制 × 二进制**（即 And）：`w = x ∧ y`：
```
w <= x
w <= y
w >= x + y - 1
w, x, y ∈ {0,1}
```

**二进制 × 连续**（`x ∈ {0,1}`, `y ∈ [0, U]`，`w = x·y`）：
```
w <= U·x           (x=0 ⇒ w=0; x=1 ⇒ w<=U，不约束)
w <= y             (w<=y)
w >= y - U·(1-x)   (x=1 ⇒ w>=y)
w >= 0
```

## 8. 上取整 / 下取整

### 8.1 上取整 `y = ⌈a/Q⌉`

直接用非线性难以建模。拆成两条不等式：
```
y >= a/Q        (即 Q·y >= a)
y - 1 < a/Q     (即 Q·(y-1) < a，严格，需 +ε)
```

整数 `a` 时：
```
a/Q <= y
y - 1 <= (a-1)/Q   等价于 Q·y <= a + Q - 1
```

**当且仅当**目标中包含 `min sum(c·y)` 时，两条中的下界约束自然收紧，可省略上界：
```python
y >= a/Q   (即 Q*y >= a)
```

典型场景：运输计算车辆数 `y[i,j] = ⌈∑f[i,j,p] / Q⌉`。

## 9. 流守恒（Flow Conservation）

### 经典写法

对有向图 `G=(V, A)`，每个节点 i，流入 - 流出 = 净供给：
```
sum_{j: (j,i) in A} f[j,i] - sum_{j: (i,j) in A} f[i,j] = b[i]
```
其中 `b[i] > 0` 表示供给节点，`b[i] < 0` 表示需求节点，`b[i] = 0` 为中转节点。

**商品流（商品 p 独立）**：
```
sum_in f[j,i,p] - sum_out f[i,j,p] = b[i,p]
```

对每个 OD 对 p，`b[o,p] = -q[p]` (起点流出)，`b[d,p] = q[p]` (终点流入)，中间节点为 0。

**注意 Gurobi 写法**：
```python
# 起点 / 终点 / 中间节点判断
def b(i, p):
    if i == origin[p]:
        return -demand[p]   # 流出
    if i == dest[p]:
        return demand[p]    # 流入
    return 0

m.addConstrs(
    (gp.quicksum(f[j,i,p] for (j,ii) in arcs if ii==i) -
     gp.quicksum(f[i,j,p] for (ii,j) in arcs if ii==i) == b(i,p)
     for i in V for p in commodities),
    name="flow_cons"
)
```

## 10. 子环消除（Subtour Elimination）

### 10.1 DFJ (Dantzig-Fulkerson-Johnson) 约束

```
sum_{i,j in S} x[i,j] <= |S| - 1,   for all S ⊂ V, 2 <= |S| <= |V|-1
```

约束数量**指数级**。实际用 **lazy callback** 动态添加，只在整数解违反时添加对应子集。

### 10.2 MTZ (Miller-Tucker-Zemlin) 约束

引入辅助变量 `u_i`（节点顺序或累计容量）：
```
u_i + 1 - u_j <= |V|·(1 - x[i,j])     for (i,j) ∈ A, i,j 非depot
或（CVRP 版本，q_i 是需求量，Q 是容量）：
u_i + q_j - u_j <= M·(1 - x[i,j])
0 <= u_i <= Q
```

- DFJ 更紧，但约束多；lazy 添加时很强
- MTZ 约束少（`|V| + |A|` 数量级），直接添加即可，但 LP 松弛较弱

### 10.3 选择

| 问题 | 推荐 |
|------|------|
| 小规模 (n < 30)，追求紧 | DFJ + lazy |
| 大规模，需快速求解 | MTZ |
| CVRP | MTZ（`u_i` 可同时表示累计容量） |

## 11. 对称性破除（Symmetry Breaking）

当变量按索引可互换且目标相同时（如 VRP 中同质车辆），求解器会反复探索等价解。引入破对称约束：

### 11.1 按容量递减

```python
# 车辆 k 的总载货 >= 车辆 k+1 的总载货
for k in range(K-1):
    m.addConstr(
        gp.quicksum(q[i]*x[i,j,k] for (i,j) in A for i in C) >=
        gp.quicksum(q[i]*x[i,j,k+1] for (i,j) in A for i in C)
    )
```

### 11.2 字典序（Lexicographic Ordering）

对二进制矩阵的行强制字典序单调：
```python
for k in range(K-1):
    m.addConstr(
        gp.quicksum(2**i * y[i,k] for i in range(n)) >=
        gp.quicksum(2**i * y[i,k+1] for i in range(n))
    )
```

### 11.3 代表元选择

"第一个"被使用的车辆必须是车辆 0；车辆 k 只有 k-1 被使用才可用：
```python
for k in range(1, K):
    m.addConstr(used[k] <= used[k-1])
```

## 12. 时间窗建模

### 12.1 硬时间窗（VRPHTW）

```python
t_i = m.addVar(lb=0, name=f"t_{i}")            # 开始服务时间
# 时间窗
m.addConstr(t_i >= a_i, name="TW_lower")
m.addConstr(t_i <= b_i, name="TW_upper")
# 弧上的时间传播（M 要紧）
m.addConstr(t_i + l_i + T_ij - t_j <= M*(1 - x[i,j]))
# M 可取 b_i + l_i + T_ij - a_j 的上界（对 i,j 单独计算最紧）
```

### 12.2 软时间窗（VRPSTW）

引入提前/延迟变量：
```python
early = m.addVar(lb=0, name=f"early_{i}")    # a_i - t_i  when t_i < a_i
late  = m.addVar(lb=0, name=f"late_{i}")     # t_i - b_i  when t_i > b_i

m.addConstr(t_i + early >= a_i)
m.addConstr(t_i - late  <= b_i)

# 目标中加入惩罚
obj += c_early * early + c_late * late
```

## 13. 分段线性（PWL）转 MIP

对非凸分段线性目标 `f(x)`，Gurobi 自动展开为 MIP：
```python
m.setPWLObj(x, xpts=[0, 5, 10, 20], ypts=[0, 10, 15, 30])
```

凸 PWL 目标可直接单纯形法处理，效率高。

手动建模 PWL 约束 `y = f(x)`：
```python
m.addGenConstrPWL(x, y, xpts=[...], ypts=[...])
```

## 14. 成本函数是阶梯（固定成本 + 变动成本）

```
开工即发生固定成本 S_j，每单位另收 p_j
```

引入 0-1 指示 `z_j`：
```
production[j] <= M * z_j         # z=0 → 不生产
cost = S_j * z_j + p_j * production[j]
```

## 15. 整数变量容差陷阱

Gurobi 判定整数可行的默认容差 `IntFeasTol = 1e-5`，所以 `x = 0.999991` 被视为 `x = 1`。如果你后续代码对解的整数性敏感（如索引数组、条件判断），**务必**：
```python
int_val = round(x.X)            # 或 int(x.X + 0.5)
# 不要：int(x.X)  —— 会把 0.9999 截断为 0
```

## 16. 方案验证与模型等价性

复杂的模型转换后（如乘法消分式、引入辅助变量），**一定要把最优解代回原始问题验证**。一个容差内的"最优解"可能在原式下违反几个数量级。

应对方法：
- 收紧容差 `FeasibilityTol = 1e-9`, `OptimalityTol = 1e-9`（但会变慢）
- 用更高精度的数值库验证
- 尝试不同模型转换路径
- 设 `NumericFocus = 3`

## 17. 集分割（Set Partitioning）建模

当决策可"枚举所有可行方案，从中选几个"时：

```
min   sum_{r in Ω} c_r · θ_r
s.t.  sum_{r in Ω} a_{i,r} · θ_r = 1,    for i ∈ C   (每客户覆盖一次)
      sum_r θ_r <= K                              (车辆数限制)
      θ_r ∈ {0,1}
```

`Ω` 是所有可行路径集合。对 VRP 这是最紧的 LP 松弛。但 `Ω` 通常指数级大，实际用**列生成** (Column Generation) 动态生成候选。

## 18. 实用速查：建模决策流程

```
有除号、幂、指数、对数、三角？
  → 非线性：用 nlfunc (13.0) 或 NLExpr

  可以乘因子消除？
  → 转二次约束 MIQCP

变量乘积 (bilinear)？
  二进制×二进制 → and/or 约束
  二进制×连续  → Big-M 转换
  连续×连续   → 二次约束（凸 or 非凸 NonConvex=2）

分段线性？ → addGenConstrPWL 或 setPWLObj

绝对值 / max / min？ → addGenConstrAbs / Max / Min

逻辑关系？ → addGenConstrAnd / Or / Indicator（优先用 indicator，避免 Big-M）

严格不等？ → + ε 或 + 1（整数）

子环？ → DFJ (lazy) 或 MTZ

对称性？ → 破对称约束（按容量递减 / 字典序 / 代表元）
```
