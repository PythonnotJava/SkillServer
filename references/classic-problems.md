# 经典运筹学问题建模

本文总结最常见的优化问题及其 Gurobi 建模方式。所有代码使用 gurobipy。

## 1. 指派问题 (Assignment Problem)

**问题**：n 个任务分配给 n 个工人，每人一个任务，每任务一人，最小化总成本。

**模型**：
- `x[i,j] ∈ {0,1}`：工人 i 做任务 j
- 每人恰一任务：`∑_j x[i,j] = 1`
- 每任务恰一人：`∑_i x[i,j] = 1`
- 目标：`min ∑_{i,j} c[i,j] * x[i,j]`

```python
import gurobipy as gp
from gurobipy import GRB

cost = [[13, 4, 7, 6],
        [1, 11, 5, 4],
        [6, 7, 2, 8],
        [1, 3, 5, 9]]
n = len(cost)

m = gp.Model("assign")
x = m.addVars(n, n, vtype=GRB.BINARY, name="x")
m.addConstrs((x.sum(i, '*') == 1 for i in range(n)), name="worker")
m.addConstrs((x.sum('*', j) == 1 for j in range(n)), name="task")
m.setObjective(gp.quicksum(cost[i][j] * x[i,j] for i in range(n) for j in range(n)),
               GRB.MINIMIZE)
m.optimize()
```

**提示**：纯指派问题（n×n 二部图）的 LP 松弛有整数最优解，所以可以直接 `vtype=GRB.CONTINUOUS`！

## 2. 0-1 背包 (Knapsack)

```python
weights = [2, 3, 4, 5]
values = [3, 4, 5, 6]
capacity = 5

m = gp.Model("knapsack")
x = m.addVars(len(values), vtype=GRB.BINARY, name="x")
m.addConstr(gp.quicksum(weights[i]*x[i] for i in range(len(values))) <= capacity)
m.setObjective(gp.quicksum(values[i]*x[i] for i in range(len(values))), GRB.MAXIMIZE)
m.optimize()
```

## 3. 工厂选址 (Facility Location)

```python
plants = ['A', 'B', 'C']
warehouses = ['X', 'Y']
fixed = {'A': 100, 'B': 80, 'C': 120}
cap = {'A': 50, 'B': 40, 'C': 60}
demand = {'X': 30, 'Y': 40}
cost = {('A','X'):2, ('A','Y'):3, ('B','X'):4, ('B','Y'):1, ('C','X'):3, ('C','Y'):2}

m = gp.Model("fl")
open_ = m.addVars(plants, vtype=GRB.BINARY, name="open")
ship = m.addVars(plants, warehouses, name="ship")

m.addConstrs((ship.sum(p, '*') <= cap[p] * open_[p] for p in plants), name="cap")
m.addConstrs((ship.sum('*', w) >= demand[w] for w in warehouses), name="dem")
m.setObjective(
    gp.quicksum(fixed[p]*open_[p] for p in plants) +
    gp.quicksum(cost[p,w]*ship[p,w] for p,w in ship),
    GRB.MINIMIZE)
m.optimize()
```

## 4. TSP (旅行商问题) — Lazy Constraints

```python
import gurobipy as gp
from gurobipy import GRB
import itertools

def solve_tsp(dist):
    n = len(dist)
    m = gp.Model("tsp")
    # x[i,j] = 是否使用边 (i,j)，i < j
    x = m.addVars([(i,j) for i in range(n) for j in range(i+1, n)],
                  vtype=GRB.BINARY, name="x")

    # 每个节点度为 2
    for i in range(n):
        m.addConstr(
            gp.quicksum(x[min(i,j), max(i,j)] for j in range(n) if i != j) == 2
        )

    m.setObjective(
        gp.quicksum(dist[i][j]*x[i,j] for i,j in x), GRB.MINIMIZE
    )

    def subtour(vals, n):
        # 从 vals 提取当前整数解的边，找最短子环
        edges = [(i,j) for (i,j) in vals if vals[i,j] > 0.5]
        unvisited = list(range(n))
        shortest = None
        while unvisited:
            cycle = []
            neighbors = unvisited
            while neighbors:
                current = neighbors[0]
                cycle.append(current)
                unvisited.remove(current)
                neighbors = [j for i,j in edges if i==current and j in unvisited] + \
                           [i for i,j in edges if j==current and i in unvisited]
            if shortest is None or len(cycle) < len(shortest):
                shortest = cycle
        return shortest

    def cb(model, where):
        if where == GRB.Callback.MIPSOL:
            vals = model.cbGetSolution(model._x)
            tour = subtour(vals, n)
            if len(tour) < n:
                # 添加 subtour elimination
                model.cbLazy(
                    gp.quicksum(model._x[min(i,j), max(i,j)]
                                for i,j in itertools.combinations(tour, 2)) <= len(tour)-1
                )

    m._x = x
    m.Params.LazyConstraints = 1
    m.optimize(cb)
    return m, x
```

## 5. 工作人员排班 (Workforce Scheduling)

```python
shifts = ['Mon1', 'Tue2', 'Wed3', ...]
workers = ['Amy', 'Bob', 'Cat', ...]
availability = {...}  # (worker, shift) -> 0/1
demand = {shift: int}
pay = {worker: float}

m = gp.Model("schedule")
x = m.addVars(workers, shifts, vtype=GRB.BINARY, name="x")

# 只能分配可用班次
for w, s in x:
    if not availability.get((w, s), 0):
        x[w, s].UB = 0

# 覆盖需求
m.addConstrs(
    (x.sum('*', s) == demand[s] for s in shifts), name="demand"
)

m.setObjective(
    gp.quicksum(pay[w]*x[w,s] for w in workers for s in shifts), GRB.MINIMIZE
)
m.optimize()
```

## 6. 多商品网络流

```python
commodities = ['C1', 'C2']
nodes = ['Det', 'Den', 'Bos', 'NY', 'Sea']
arcs = gp.tuplelist([('Det','Bos'), ('Det','NY'), ('Den','NY'), ...])
capacity = {arc: cap for arc in arcs}
cost = {(c,a): ... for c in commodities for a in arcs}
inflow = {(c,n): ... for c in commodities for n in nodes}

m = gp.Model("mcflow")
flow = m.addVars(commodities, arcs, name="flow")

# 容量
m.addConstrs(
    (flow.sum('*', i, j) <= capacity[i,j] for i,j in arcs), name="cap"
)
# 流量守恒
m.addConstrs(
    (gp.quicksum(flow[c, i, j] for i,j in arcs.select('*', n)) -
     gp.quicksum(flow[c, n, j] for i,j in arcs.select(n, '*')) == inflow[c,n]
     for c in commodities for n in nodes),
    name="node"
)
m.setObjective(
    gp.quicksum(cost[c, i, j] * flow[c, i, j]
                for c in commodities for i,j in arcs), GRB.MINIMIZE
)
m.optimize()
```

## 7. 投资组合优化 (Markowitz)

```python
import numpy as np
# returns: 预期收益率向量
# sigma: 协方差矩阵
# target: 目标收益率

n = len(returns)
m = gp.Model("portfolio")
x = m.addVars(n, lb=0, ub=1, name="x")

m.addConstr(x.sum() == 1, name="budget")
m.addConstr(gp.quicksum(returns[i]*x[i] for i in range(n)) >= target, name="ret")

# 风险 = x' Σ x
risk = gp.quicksum(sigma[i][j]*x[i]*x[j] for i in range(n) for j in range(n))
m.setObjective(risk, GRB.MINIMIZE)
m.optimize()
```

## 8. 车辆路径 (VRP) — 简化版

```python
# 节点 0 是车场，1..n 是客户
depot = 0
customers = list(range(1, n+1))
K = 3   # 车辆数

m = gp.Model("vrp")
x = m.addVars([(i,j,k) for i in range(n+1) for j in range(n+1) if i!=j for k in range(K)],
              vtype=GRB.BINARY, name="x")

# 每客户被访问一次
m.addConstrs(
    (gp.quicksum(x[i,j,k] for i in range(n+1) if i!=j for k in range(K)) == 1
     for j in customers), name="visit"
)
# 每车从车场出发并返回
m.addConstrs(
    (gp.quicksum(x[depot,j,k] for j in customers) <= 1 for k in range(K)), name="out"
)
m.addConstrs(
    (gp.quicksum(x[i,depot,k] for i in customers) <= 1 for k in range(K)), name="in"
)
# 流量守恒
m.addConstrs(
    (gp.quicksum(x[i,h,k] for i in range(n+1) if i!=h) ==
     gp.quicksum(x[h,j,k] for j in range(n+1) if j!=h)
     for h in range(n+1) for k in range(K)), name="flow"
)
# + 容量约束、子环消除 (lazy) …
```

## 9. N 皇后 (使用 Matrix API)

```python
import numpy as np
from scipy import sparse

n = 8
m = gp.Model("nqueens")
X = m.addMVar((n, n), vtype=GRB.BINARY)
m.setObjective(X.sum(), GRB.MAXIMIZE)

# 每行至多一个
m.addConstr(X.sum(axis=1) <= 1)
# 每列至多一个
m.addConstr(X.sum(axis=0) <= 1)
# 每对角线至多一个
for k in range(-(n-1), n):
    m.addConstr(X.diagonal(offset=k).sum() <= 1)
for k in range(-(n-1), n):
    m.addConstr(np.fliplr(X).diagonal(offset=k).sum() <= 1)
m.optimize()
```

## 10. 生产-库存 (Lot Sizing)

经典动态批量：决策每期生产量和库存，满足需求，最小化成本 (生产 + 固定开机 + 库存)。

```python
T = 12   # 月数
demand = [...]
p_cost = [...]
h_cost = [...]
s_cost = [...]
cap = [...]

m = gp.Model("lotsize")
x = m.addVars(T, name="produce")      # 产量
I = m.addVars(T, name="inventory")    # 期末库存
y = m.addVars(T, vtype=GRB.BINARY)    # 是否开机

m.addConstrs((x[t] <= cap[t] * y[t] for t in range(T)), name="cap")
# 库存平衡：I[t] = I[t-1] + x[t] - d[t]
m.addConstr(I[0] == 0 + x[0] - demand[0])
m.addConstrs((I[t] == I[t-1] + x[t] - demand[t] for t in range(1, T)))

m.setObjective(
    gp.quicksum(p_cost[t]*x[t] + s_cost[t]*y[t] + h_cost[t]*I[t]
                for t in range(T)), GRB.MINIMIZE
)
m.optimize()
```

## 更多

官方示例名称速查：`diet`, `facility`, `mip1`, `workforce1-5`, `tsp`, `matrix1`, `matrix2`, `netflow`, `portfolio`, `sudoku`, `gc_pwl`, `gc_pwl_func`, `gc_funcnonlinear`, `lp`, `lpmod`, `callback`, `feasopt`, `sensitivity`, `multiobj`, `multiscenario`, `batchmode`, `tune`, `bilinear`, `qp`, `qcp`, `sos`, `poolsearch`, `params`, `fixanddive`, `genconstr`, `genconstrnl`, `piecewise`。

位置：Gurobi 安装目录 `examples/python/`、`examples/c/` 等。
