# 车辆路径规划问题 (VRP) 完全指南

VRP 是最经典的 NP-hard 组合优化问题之一。本文系统介绍常见变体及 Gurobi 建模方式。

## 1. VRP 家族一览

| 缩写 | 中文名 | 增加的特性 |
|------|--------|-----------|
| TSP | 旅行商问题 | 单车访问所有点 |
| CVRP | 带容量约束 VRP | 车辆有容量上限 |
| MDVRP | 多车场 VRP | 多个配送中心 |
| VRPTW | 带时间窗 VRP | 客户有时间窗 |
| VRPPD | 取送货 VRP | 客户既取货又送货 |
| MTVRP | 多行程 VRP | 一车可跑多趟 |
| HVRP | 异质 VRP | 车辆有不同类型 |
| SDVRP | 可分拆 VRP | 一客户可多车服务 |

## 2. CVRP（容量约束 VRP）

### 问题描述

给定客户点集 C、配送中心 o、车队 K（容量均为 Q）、距离成本 c_{ij}。每车从 o 出发，访问若干客户后返回 o。目标：最小化总行驶成本，要求每客户恰好一车服务，每车载货量不超 Q。

### 数学语言描述

`G = (V, A)`，`V = C ∪ {o, d}`（d 是 o 的复制点用于区分发车/归场），`A = {(i,j) | ∀i,j ∈ V, i ≠ j}` 排除：
- `(o, d)` 弧（不允许空跑）
- 以 o 为终点的弧 `(*, o)`
- 以 d 为起点的弧 `(d, *)`
- 自环 `(i, i)`

### CVRP1-1：三下标 x^k_{ij} + DFJ 约束

```
min   ∑_{k ∈ K} ∑_{(i,j) ∈ A} c_{ij} · x^k_{ij}

s.t.  ∑_{k ∈ K} ∑_{j ∈ V} x^k_{ij} = 1,                ∀i ∈ C            (客户访问)
      ∑_{j ∈ C} x^k_{oj} = ∑_{i ∈ C} x^k_{id} <= 1,    ∀k ∈ K            (发车归场)
      ∑_{j ∈ V} x^k_{ij} = ∑_{j ∈ V} x^k_{ji},         ∀k ∈ K, i ∈ C    (流平衡)
      ∑_{i ∈ C} ∑_{j ∈ V} q_i · x^k_{ij} <= Q,         ∀k ∈ K            (容量)
      ∑_{i ∈ S} ∑_{j ∈ S} x^k_{ij} <= |S| - 1,         ∀S ⊂ C, 2≤|S|≤|V|-1, ∀k  (DFJ)
      x^k_{ij} ∈ {0,1}
```

**特点**：DFJ 数量指数级；实际用 **lazy callback** 动态添加。

### CVRP1-2：三下标 + MTZ 约束

引入连续变量 `u^k_i`（车 k 到 i 时累计需求）：

```
min   ∑_{k ∈ K} ∑_{(i,j) ∈ A} c_{ij} · x^k_{ij}

s.t.  (前 4 组约束同 CVRP1-1)
      u^k_i + q_j - u^k_j <= M·(1 - x^k_{ij}),  ∀(i,j) ∈ A, k ∈ K, M = Q
      0 <= u^k_i <= Q,                            ∀i ∈ V, k ∈ K
      x^k_{ij} ∈ {0,1}
```

**特点**：多 `|K|·|V|` 连续变量 + `|A|·|K|` 约束，可直接求解器求解；LP 松弛比 DFJ 弱，但无需回调。

### CVRP2：双下标 x_{ij} + MTZ

由于车辆同质，可把**车辆编号下标消除**：

```
min   ∑_{(i,j) ∈ A} c_{ij} · x_{ij}

s.t.  ∑_{j ∈ V} x_{ij} = 1,                         ∀i ∈ C
      ∑_{j ∈ C} x_{oj} - ∑_{i ∈ C} x_{id} = 0                         (出发=回场)
      ∑_{j ∈ V} x_{ij} - ∑_{j ∈ V} x_{ji} = 0,     ∀j ∈ C            (流平衡)
      u_i + q_j - u_j <= M·(1 - x_{ij}),            ∀(i,j) ∈ A
      0 <= u_i <= Q,                                 ∀i ∈ V
      x_{ij} ∈ {0,1}
```

**规模对比**：
| 模型 | 变量数 | 约束数 |
|------|--------|--------|
| CVRP1-1 | O(\|K\|·\|V\|²) + 2^C·\|K\| | O(\|K\|·\|V\|²) + 指数 |
| CVRP1-2 | O(\|K\|·\|V\|²) | O(\|K\|·\|V\|²) |
| CVRP2 | O(\|V\|²) | O(\|V\|²) |

**注意**：CVRP2 失去异质车辆建模能力。若车辆有不同容量，必须用三下标。

### CVRP3：集分割（列生成用）

把每条可行路径 `r` 作为 0-1 决策变量 `θ_r`：

```
min  ∑_{r ∈ Ω} c_r · θ_r

s.t. ∑_r a_{ir} · θ_r = 1,   ∀i ∈ C       (每客户恰覆盖一次)
     ∑_r θ_r <= |K|
     θ_r ∈ {0,1}
```

`Ω` 是所有可行路径集合，`a_{ir} = 1` 当 `r` 包含 `i`。LP 松弛最紧，但 `|Ω|` 指数级，必须用**列生成**动态添加。

### CVRP Gurobi 代码（CVRP2，Python）

```python
import gurobipy as gp
from gurobipy import GRB

def solve_cvrp(customers, depot_id, demand, cost, Q):
    """
    customers: list 客户编号（不含 depot）
    depot_id: 车场编号
    demand:   dict, demand[i]
    cost:     dict, cost[i,j]
    Q:        车辆容量
    """
    V = customers + [depot_id]
    A = [(i,j) for i in V for j in V if i != j and (i,j) != (depot_id, depot_id)]

    m = gp.Model("cvrp")
    x = m.addVars(A, vtype=GRB.BINARY, name="x")
    u = m.addVars(V, lb=0, ub=Q, name="u")

    # 目标
    m.setObjective(gp.quicksum(cost[i,j] * x[i,j] for (i,j) in A), GRB.MINIMIZE)

    # 客户访问
    for i in customers:
        m.addConstr(gp.quicksum(x[i,j] for j in V if j != i) == 1, name=f"visit_{i}")

    # 流平衡（客户）
    for i in customers:
        m.addConstr(
            gp.quicksum(x[i,j] for j in V if j != i) ==
            gp.quicksum(x[j,i] for j in V if j != i),
            name=f"flow_{i}"
        )

    # MTZ + 容量
    for (i,j) in A:
        if i in customers and j in customers:
            m.addConstr(u[i] + demand[j] - u[j] <= Q*(1 - x[i,j]),
                        name=f"mtz_{i}_{j}")
    # 车场出发 u=0
    m.addConstr(u[depot_id] == 0)

    m.optimize()

    if m.Status == GRB.OPTIMAL:
        print(f"最优成本: {m.ObjVal:.2f}")
        used = [(i,j) for (i,j) in A if x[i,j].X > 0.5]
        return m.ObjVal, used
```

### CVRP1-1 + Lazy DFJ 回调

```python
def solve_cvrp_dfj(customers, depot_id, demand, cost, Q, K):
    V = customers + [depot_id]
    A = [(i,j) for i in V for j in V if i != j]

    m = gp.Model("cvrp_dfj")
    x = m.addVars(K, A, vtype=GRB.BINARY, name="x")

    m.setObjective(
        gp.quicksum(cost[i,j] * x[k,i,j] for k in range(K) for (i,j) in A),
        GRB.MINIMIZE
    )
    # 客户访问
    for i in customers:
        m.addConstr(
            gp.quicksum(x[k,i,j] for k in range(K) for j in V if j != i) == 1,
            name=f"visit_{i}"
        )
    # 每车容量
    for k in range(K):
        m.addConstr(
            gp.quicksum(demand[i] * x[k,i,j]
                        for (i,j) in A if i in customers) <= Q,
            name=f"cap_{k}"
        )
    # 流平衡
    for k in range(K):
        for i in customers:
            m.addConstr(
                gp.quicksum(x[k,i,j] for j in V if j != i) ==
                gp.quicksum(x[k,j,i] for j in V if j != i)
            )
        # 发车/归场 <= 1
        m.addConstr(gp.quicksum(x[k,depot_id,j] for j in customers) <= 1)
        m.addConstr(gp.quicksum(x[k,i,depot_id] for i in customers) <= 1)

    def find_subtours(k, sol):
        """找车 k 的所有非经过 depot 的环"""
        edges = [(i,j) for (i,j) in A if sol[k,i,j] > 0.5]
        visited = set()
        subtours = []
        for start in customers:
            if start in visited:
                continue
            cycle = [start]; visited.add(start); cur = start
            while True:
                nxt = None
                for (i,j) in edges:
                    if i == cur and j not in visited and j != depot_id:
                        nxt = j; break
                if nxt is None or nxt == depot_id:
                    break
                cycle.append(nxt); visited.add(nxt); cur = nxt
            if len(cycle) >= 2 and depot_id not in cycle:
                subtours.append(cycle)
        return subtours

    def cb(model, where):
        if where == GRB.Callback.MIPSOL:
            sol = model.cbGetSolution(model._x)
            for k in range(K):
                for S in find_subtours(k, sol):
                    model.cbLazy(
                        gp.quicksum(model._x[k,i,j]
                                    for i in S for j in S if i != j) <= len(S) - 1
                    )

    m._x = x
    m.Params.LazyConstraints = 1
    m.optimize(cb)
    return m
```

## 3. MDVRP（多车场 VRP）

两种主要变体：
- **MDVRP1**：车辆可返回任意车场，每车场发车/收车数相等
- **MDVRP2**：车辆必须返回原车场

### MDVRP1（允许跨车场）

双下标 `x_{ij}` + MTZ。关键约束：

```
∑_{j ∈ V} x_{ij} = 1,                    ∀i ∈ C              (客户访问)
∑_{j ∈ C} x_{ij} <= δ_i,                 ∀i ∈ D              (车场发车<=车队规模)
∑_{j ∈ V} x_{ij} - ∑_{j ∈ V} x_{ji} = 0, ∀j ∈ C              (客户流平衡)
∑_{j ∈ C} x_{ij} - ∑_{j ∈ C} x_{ji} = 0, ∀i ∈ D              (车场收发平衡)
u_i + q_j - u_j <= M(1 - x_{ij}),         ∀(i,j), i,j ∉ D    (客户→客户)
u_i + q_j - Q  <= M(1 - x_{ij}),          ∀(i,j), j ∈ D      (客户→车场)
∑_{j ∈ D} x_{ij} = 0,                    ∀i ∈ D              (禁止车场直接到车场)
0 <= u_i <= Q
```

### MDVRP2（必须返回原车场）

需要对每个车场复制为 `o_i` 和 `d_i` 两个节点。决策变量 `x^k_{ij}` 含车辆编号。

约束：
```
∑_{k ∈ K} ∑_{j ∈ V} x^k_{ij} = 1,            ∀i ∈ C
∑_{i ∈ D_o} ∑_{j ∈ C} x^k_{ij} <= 1,          ∀k ∈ K       (每车最多使用一次)
∑_{k} ∑_j x^k_{ij} <= δ_i,                   ∀i ∈ D_o     (发车数<=规模)
∑_{j ∈ V} x^k_{ij} - ∑_{j ∈ V} x^k_{ji} = 0, ∀k, j ∈ C
∑_{j ∈ C} x^k_{ij} - ∑_{j ∈ C} x^k_{jl} = 0, ∀k, i ∈ D_o, l ∈ D_d, l = i  (同车场)
u^k_i + q_j - u^k_j <= M(1 - x^k_{ij}),       ∀(i,j), i,j ∉ D_o ∪ D_d
```

## 4. VRPTW（带时间窗）

### 硬时间窗 (VRPHTW)

双下标 `x_{ij}` 模型：

```
min  ∑_{(i,j) ∈ A} c_{ij} · x_{ij}

s.t. ∑_{k} ∑_j x^k_{ij} = 1,                   ∀i ∈ C
     ∑_j x^k_{oj} = ∑_i x^k_{id} <= 1,          ∀k
     流平衡, 容量约束 (同 CVRP)

     # 时间窗
     a_i <= t_i <= b_i,                        ∀i ∈ V
     t_i + l_i + T_{ij} - t_j <= M(1 - x_{ij}), ∀(i,j) ∈ A

     x_{ij} ∈ {0,1}
```

`l_i` 是 i 处服务时间，`T_{ij}` 是行驶时间。`M` 取 `max(0, b_i + l_i + T_{ij} - a_j)` 最紧。

### 软时间窗 (VRPSTW)

三种常见设置：
1. **VRPSTW1**：允许延迟（含惩罚），不允许提前
2. **VRPSTW2**：允许提前和延迟（都含惩罚），允许等待
3. **VRPSTW3**：允许提前和延迟，但不允许等待

#### VRPSTW1（延迟惩罚）

```
t_i + late_i >= a_i       (可提前到达但等到 a_i 才服务，late_i = max(0, a_i - t_i + L))
```

引入延迟变量：
```python
late = m.addVars(C, lb=0, name="late")
m.addConstr(t_i - b_i <= late[i])       # late = max(0, t_i - b_i)
# 目标中加入 c_late * late[i]
```

### 时间窗建模公共陷阱

- `M` 过大 → LP 松弛弱、数值不稳
- 客户间行驶时间矩阵**不满足三角不等式**时，需额外处理
- 若解不存在（硬时间窗下不可行），考虑转软时间窗

## 5. 常见扩展

### 5.1 异质车辆 (HVRP)

不同车 k 有不同容量 `Q_k` 和成本 `c^k_{ij}`。必须用三下标模型 `x^k_{ij}`。

### 5.2 多行程 (MTVRP)

一车可执行多次"车场→客户→车场"循环。打破 `∑_j x^k_{oj} <= 1` 的限制，改为与时间上限 `T_max^k` 关联：
```
∑_{(i,j)} T_{ij} · x^k_{ij} <= T_max^k
```

### 5.3 取送货 (VRPPD)

每客户既有取货量 `p_i` 又有送货量 `d_i`：
- Pickup-Delivery with Pairs（成对）：i 的货必须送到 j
- One-to-many：从车场出发送货给若干客户

### 5.4 可分拆 (SDVRP)

允许一个客户被多辆车服务。`x^k_{ij}` 依然二进制，但需额外变量 `y^k_i`（车 k 给客户 i 服务的量），约束：
```
∑_k y^k_i = q_i
y^k_i <= Q * ∑_j x^k_{ij}
```

## 6. 对称性破除

CVRP 三下标模型有明显对称性：K 辆同质车的路径置换等价。可加约束：
```
# 车辆 k 总载货 >= 车辆 k+1 总载货
∑_{i,j} q_i · x^{k-1}_{ij} >= ∑_{i,j} q_i · x^k_{ij},   ∀k ∈ K \ {1}

# 或：车辆 k 必须访问编号最小的剩余未分配客户
# （更严但可能切掉最优解，需谨慎）
```

## 7. 求解技巧

1. **规模 n < 30**：CVRP1-1 + DFJ lazy 最优
2. **规模 30-100**：CVRP2 + MTZ 常规 MIP
3. **规模 >100**：考虑集分割 + 列生成 / 启发式（Saving, LKH, GA）
4. **整数规划求解参数**：
   - `MIPFocus = 1` 先找可行解
   - `Cuts = 2` 激进切割（VRP 有很好的切割技术）
   - `Symmetry = 2` 强检测对称性
5. **暖启动**：用启发式（如最近邻）生成初始解作为 MIP start

## 8. VRP 建模完整模板（带时间窗）

见 `assets/templates/cvrp_template.py` 和 `assets/templates/vrptw_template.py`.
