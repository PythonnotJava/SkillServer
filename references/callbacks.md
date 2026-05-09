# Gurobi 回调 (Callbacks) 指南

回调允许在求解过程中**监控进度**、**动态终止**、**添加 lazy constraints / user cuts**、**注入启发式解**。

## 基本结构 (gurobipy)

```python
import gurobipy as gp
from gurobipy import GRB

def mycb(model, where):
    if where == GRB.Callback.MIP:
        # 通用 MIP 回调：每隔一段时间触发
        nodecnt = model.cbGet(GRB.Callback.MIP_NODCNT)
        objbst  = model.cbGet(GRB.Callback.MIP_OBJBST)  # 当前最优
        objbnd  = model.cbGet(GRB.Callback.MIP_OBJBND)  # 最佳下界
        # 自定义终止：差距 < 10% 就退出
        if abs(objbst - objbnd) < 0.1 * (1.0 + abs(objbst)):
            model.terminate()

m.optimize(mycb)
```

13.0 起可通过 `wheres` 参数过滤只关心的事件，减少 Remote Services 调用开销：

```python
m.optimize(mycb, wheres=[GRB.Callback.MIP, GRB.Callback.MIPSOL])
```

## where 值 (Python)

| `where` 常量 | 触发时机 |
|--------------|----------|
| `GRB.Callback.POLLING` | 轮询（可忽略） |
| `GRB.Callback.PRESOLVE` | 预处理进度 |
| `GRB.Callback.SIMPLEX` | 单纯形进度 |
| `GRB.Callback.BARRIER` | 内点法进度 |
| `GRB.Callback.MESSAGE` | 求解器日志消息 |
| `GRB.Callback.MIP` | MIP 进度（周期性） |
| `GRB.Callback.MIPSOL` | 找到新整数可行解 |
| `GRB.Callback.MIPNODE` | 处理一个 B&B 节点 |
| `GRB.Callback.MULTIOBJ` | 多目标切换目标 |
| `GRB.Callback.IIS` | IIS 计算进度 |

## cbGet 可查询的常量

### MIP 通用 (`where == MIP`)
`MIP_OBJBST`, `MIP_OBJBND`, `MIP_NODCNT`, `MIP_SOLCNT`, `MIP_CUTCNT`, `MIP_NODLFT`, `MIP_ITRCNT`.

### MIPSOL (新解)
`MIPSOL_OBJ`, `MIPSOL_OBJBST`, `MIPSOL_OBJBND`, `MIPSOL_NODCNT`, `MIPSOL_SOLCNT`.
`model.cbGetSolution(vars)` 获取这个新解的变量值。

### MIPNODE (节点处理)
`MIPNODE_STATUS`, `MIPNODE_OBJBST`, `MIPNODE_OBJBND`, `MIPNODE_NODCNT`, `MIPNODE_SOLCNT`.
`model.cbGetNodeRel(vars)` 获取节点 LP 松弛解（仅当 status==OPTIMAL）。

### SIMPLEX
`SPX_OBJVAL`, `SPX_PRIMINF`, `SPX_DUALINF`, `SPX_ISPERT`, `SPX_ITRCNT`.

### BARRIER
`BARRIER_PRIMOBJ`, `BARRIER_DUALOBJ`, `BARRIER_PRIMINF`, `BARRIER_DUALINF`, `BARRIER_COMPL`, `BARRIER_ITRCNT`.

### IIS
`IIS_CONSTRMIN/MAX/GUESS`, `IIS_BOUNDMIN/MAX/GUESS`.

### MESSAGE
`MSG_STRING`（可重定向日志）.

## 回调中允许的操作

| 动作 | API |
|------|-----|
| 查询求解信息 | `cbGet(what)` |
| 查询当前 incumbent | `cbGetSolution(vars)` (仅 `MIPSOL`) |
| 查询 LP 松弛 | `cbGetNodeRel(vars)` (仅 `MIPNODE`) |
| 提供启发式整数解 | `cbSetSolution(vars, vals)` → `cbUseSolution()` (仅 `MIPNODE`) |
| 添加 Lazy Constraint | `cbLazy(constr)` (仅 `MIPSOL` 或 `MIPNODE`) |
| 添加 User Cut | `cbCut(constr)` (仅 `MIPNODE`) |
| 终止优化 | `model.terminate()` |
| 修改终止参数 | `cbSetParam(param, val)` |

## Lazy Constraints（延迟约束）

典型用例：TSP 子环消除。完整约束集合指数级，只有当候选整数解违反时才添加。

```python
m.Params.LazyConstraints = 1   # 必须打开！

def subtour_callback(model, where):
    if where == GRB.Callback.MIPSOL:
        vals = model.cbGetSolution(model._x)
        # 找到当前解中的子环
        tour = find_shortest_subtour(vals)
        if len(tour) < n:
            # 添加切除该子环的约束
            model.cbLazy(
                gp.quicksum(model._x[i,j] for i,j in itertools.combinations(tour, 2))
                <= len(tour) - 1
            )

m._x = x     # 把变量存到 model 上方便 callback 用
m.optimize(subtour_callback)
```

**Lazy 约束不是 user cuts**：lazy 是逻辑上必需的约束（解必须满足），user cut 是**有效的**松弛加强（解可以满足）。

## User Cuts

```python
m.Params.PreCrush = 1   # 必须：允许把原模型割翻译到 presolved 模型

def usercut_callback(model, where):
    if where == GRB.Callback.MIPNODE:
        if model.cbGet(GRB.Callback.MIPNODE_STATUS) == GRB.OPTIMAL:
            vals = model.cbGetNodeRel(model._vars)
            if some_cut_violated(vals):
                model.cbCut(my_cut)

m.optimize(usercut_callback)
```

## 注入启发式解

```python
def heur_callback(model, where):
    if where == GRB.Callback.MIPNODE:
        rel = model.cbGetNodeRel(model._vars)
        heur_sol = round_and_repair(rel)
        model.cbSetSolution(model._vars, heur_sol)
        obj = model.cbUseSolution()   # 返回目标或 INFINITY 如果解不可行
```

## 自定义终止示例

```python
# 找到首个可行解后再给 60 秒
def early_stop(model, where):
    if where == GRB.Callback.MIPSOL:
        if not model._found_first:
            model._found_first = True
            model._stop_time = time.time() + 60
    elif where == GRB.Callback.MIP:
        if model._found_first and time.time() > model._stop_time:
            model.terminate()

m._found_first = False
m.optimize(early_stop)
```

## C API 对应

| gurobipy | C |
|----------|---|
| `model.cbGet(what)` | `GRBcbget(cbdata, where, what, &val)` |
| `model.cbGetSolution(vars)` | `GRBcbget(cbdata, where, GRB_CB_MIPSOL_SOL, sol)` |
| `model.cbLazy(constr)` | `GRBcblazy(cbdata, nz, cind, cval, sense, rhs)` |
| `model.cbCut(constr)` | `GRBcbcut(cbdata, nz, cind, cval, sense, rhs)` |
| `model.cbSetSolution(...); cbUseSolution()` | `GRBcbsolution(cbdata, sol, &objval)` |
| `model.terminate()` | `GRBterminate(model)` |

## 线程安全

- MIP 回调可能从多个线程调用。共享数据结构要加锁。
- Gurobi 保证**同一时刻只有一个回调在执行**（per model），所以回调函数本身是串行的。
- 但如果回调访问 Python 全局变量，要当心**并行 MIP** 下的回调被反复触发。

## Tuner 中的回调 (13.0)

```python
def tune_cb(model, where):
    # tuner 用 POLLING/MESSAGE where 值
    if where == GRB.Callback.POLLING:
        if time.time() > deadline:
            model.terminate()

m.tune(tune_cb)
```

## 完整示例：带进度打印 + 自定义终止 + lazy cut

见 `assets/templates/callback_template.py`。
