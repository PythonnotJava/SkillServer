# gurobipy (Python API) 实战指南

Gurobi 官方推荐的 API，支持 Python 3.10-3.14。

## 安装

```bash
pip install gurobipy
# 或
conda install -c gurobi gurobi
```

无许可证可以运行规模受限的模型（免费试用）；学术用户 / 商业用户需要 `grbgetkey` 安装许可证。

## 最小骨架

```python
import gurobipy as gp
from gurobipy import GRB

# 推荐使用 context manager 自动清理资源和许可证
with gp.Env() as env, gp.Model(env=env) as m:
    x = m.addVar(name="x")
    y = m.addVar(name="y")
    m.addConstr(x + y >= 1)
    m.setObjective(x + 2*y, GRB.MINIMIZE)
    m.optimize()

    if m.Status == GRB.OPTIMAL:
        print(f"最优值: {m.ObjVal}")
        print(f"x = {x.X}, y = {y.X}")
```

不使用 `Env` 时 Gurobi 用隐式默认环境，简单脚本可省略。

## 核心数据结构

### tuplelist

带索引的列表，支持快速模式匹配：

```python
edges = gp.tuplelist([(1,2), (1,3), (2,3), (2,4), (3,4)])
out_of_1 = edges.select(1, '*')  # 所有从节点 1 出发的边
into_4   = edges.select('*', 4)
```

### tupledict

变量字典，支持 `sum()` 和 `prod()` 切片求和：

```python
x = m.addVars([(i,j) for i in range(3) for j in range(3)], name="x")
# x 是 tupledict

# 切片求和：固定 i=1，对所有 j 求和
m.addConstr(x.sum(1, '*') <= 10)

# 按权重求和：对每个 i，sum_j c[i,j] * x[i,j]
m.addConstr(x.prod(c, 0, '*') >= demand)
```

### multidict

一次从字典数据创建键、值元组：

```python
# 三列：节点、容量、成本
nodes, capacity, cost = gp.multidict({
    'A': [10, 2.5],
    'B': [8,  1.2],
    'C': [15, 3.0]
})
# nodes = ['A','B','C']
# capacity = {'A':10, 'B':8, 'C':15}
# cost = {'A':2.5, 'B':1.2, 'C':3.0}
```

### MVar (Matrix Variable)

适合线性代数风格建模：

```python
import numpy as np
from scipy import sparse

A = sparse.csr_matrix([[1, 2, 3], [1, 1, 0]])
b = np.array([4, 1])
c = np.array([1, 1, 2])

m = gp.Model()
x = m.addMVar(shape=3, vtype=GRB.BINARY, name="x")
m.setObjective(c @ x, GRB.MAXIMIZE)
m.addConstr(A @ x <= b)
m.optimize()
print(x.X)
```

## 表达式构造

```python
# 线性表达式
expr = 2*x + 3*y - z

# 长求和：一定用 quicksum！
big = gp.quicksum(c[i]*x[i] for i in range(10000))  # O(n)
# 不要用 sum(c[i]*x[i] for i in ...) —— 它是 O(n²)

# 二次表达式
q = x*x + 2*x*y + y*y

# 从 LinExpr 迭代各项（13.0 新）
for coef, var in expr.linTerms():
    print(coef, var.VarName)
```

## 懒更新 (Lazy Update)

默认 `UpdateMode=1`：新添加的对象可立即在约束/目标中使用。但有时需显式 `m.update()` 把未提交的修改同步到 Gurobi：

```python
x = m.addVar()
# 此时查询 x.VarName 可能不可见
m.update()
# 现在所有查询都反映最新状态
```

写 LP/MPS 文件、`getVars()`、`getConstrs()` 之前通常需要 `update()`。

## 读写模型

```python
m = gp.read("model.mps")   # 支持 .mps/.lp/.rew/.rlp/.ilp/.mps.gz/.mps.bz2
m.write("model.lp")        # 根据后缀决定格式
m.write("solution.sol")    # 解
m.write("solution.json")   # JSON 解
m.write("basis.bas")       # 单纯形基
m.write("mipstart.mst")    # MIP 起始
m.write("attr.attr")       # 属性
m.write("params.prm")      # 参数
```

## 参数与属性

```python
# 参数（算法行为）
m.Params.TimeLimit = 60
m.Params.MIPGap = 0.01
m.Params.OutputFlag = 0  # 关闭日志
m.setParam('Threads', 8)

# 属性（模型/解信息）
m.ObjVal          # 目标值
m.Status          # 求解状态（见 attributes.md）
x.X               # 变量解
x.RC              # 简约成本（LP）
c.Pi              # 对偶变量（LP）
c.Slack           # 松弛
m.MIPGap          # 当前差距
m.Runtime         # 求解时间
```

## 回调（简化版）

```python
def my_callback(model, where):
    if where == GRB.Callback.MIP:
        nodecnt = model.cbGet(GRB.Callback.MIP_NODCNT)
        if nodecnt > 100000:
            model.terminate()
    elif where == GRB.Callback.MIPSOL:
        # 新找到可行整数解
        obj = model.cbGet(GRB.Callback.MIPSOL_OBJ)
        x_vals = model.cbGetSolution(x_vars)

m.optimize(my_callback)
```

13.0 起 `optimize` / `optimizeAsync` / `computeIIS` 支持 `wheres=[...]` 参数过滤只关心的回调点，提升远程运行性能。完整列表见 `callbacks.md`。

## 调参

```python
# 自动调参
m.tune()
for i in range(m.TuneResultCount):
    m.getTuneResult(i)
    m.write(f"tune{i}.prm")
```

13.0 新：`TuneIgnoreSettings` 跳过已测过的参数组合；`tune()` 也可接收 callback。

## 常见陷阱

1. **`sum` 慢**：`quicksum(...)` 总是更快。大模型建议全部替换。
2. **解完才能查 `X`**：优化前 `x.X` 不可用，先检查 `m.Status`。
3. **整数解微小浮点值**：`x.X` 可能是 `0.9999999` 而不是 `1`。使用 `round(x.X)` 或 `int(x.X + 0.5)`，并牢记 `IntFeasTol`。
4. **多次调用 `optimize`**：默认是 warm start。如需完全重解，`m.reset()`；如需清除参数调整，也要重置。
5. **复用 Env**：同一脚本里多个模型共享 Env 可节省许可证检查时间。
6. **`numpy` 兼容**：变量可直接 `@`、`*`、`+` numpy 数组。
7. **解池（solution pool）**：`m.Params.PoolSearchMode=2; m.Params.PoolSolutions=k` 保留 k 个可行解；用 `m.Params.SolutionNumber=i; x.Xn` 查询第 i 个。13.0 起 `Xn` 改名为 `PoolNX`，`PoolObjVal` 改名为 `PoolNObjVal`。
8. **上下文管理器**：生产代码必须用 `with gp.Env() as env: ...` 确保许可证释放。
9. **模型修改后 `Status`**：重要属性如 `Status`、`ObjVal` 在修改模型后会变成 `LOADED`，不再是上次解的值。
10. **日志重定向**：`m.Params.LogFile = "solve.log"` + `m.Params.LogToConsole = 0`。

## 典型完整示例（工厂选址）

```python
import gurobipy as gp
from gurobipy import GRB

plants = ["Baytown", "Beaumont", "Baton Rouge"]
warehouses = ["Houston", "Dallas", "SA"]
fixed_cost = {"Baytown":7000, "Beaumont":4500, "Baton Rouge":4200}
capacity = {"Baytown":20, "Beaumont":22, "Baton Rouge":17}
demand = {"Houston":15, "Dallas":18, "SA":14}
trans = {("Baytown","Houston"):4000, ("Baytown","Dallas"):5000, ...}

with gp.Env() as env, gp.Model(env=env, name="facility") as m:
    open_ = m.addVars(plants, vtype=GRB.BINARY, name="open")
    ship = m.addVars(plants, warehouses, vtype=GRB.CONTINUOUS, name="ship")

    # 容量
    m.addConstrs(
        (ship.sum(p, '*') <= capacity[p] * open_[p] for p in plants),
        name="cap"
    )
    # 需求
    m.addConstrs(
        (ship.sum('*', w) >= demand[w] for w in warehouses),
        name="dem"
    )

    m.setObjective(
        gp.quicksum(fixed_cost[p]*open_[p] for p in plants) +
        gp.quicksum(trans[p,w]*ship[p,w] for p in plants for w in warehouses),
        GRB.MINIMIZE
    )

    m.optimize()

    if m.Status == GRB.OPTIMAL:
        for p in plants:
            if open_[p].X > 0.5:
                print(f"Open {p}, shipments:")
                for w in warehouses:
                    if ship[p,w].X > 1e-6:
                        print(f"  -> {w}: {ship[p,w].X:.1f}")
```
