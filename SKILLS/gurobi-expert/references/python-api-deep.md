# gurobipy API 深度指南（补充）

本文补充了日常建模中常用但容易遗漏的 gurobipy API 细节。

## 1. 变量创建的所有参数

```python
m.addVar(
    lb=0.0,                   # 下界
    ub=GRB.INFINITY,          # 上界
    obj=0.0,                  # 线性目标系数（等价于之后在 setObjective 中加）
    vtype=GRB.CONTINUOUS,     # 类型
    name="",                  # 名称
    column=None,              # 该变量在已有约束中的系数（Column 对象），用于列生成
)

# 批量
m.addVars(
    *indices,                 # 可多个索引集合，笛卡尔积
    lb=0.0, ub=..., obj=..., vtype=..., name="",
)
```

### 使用 `column` 参数（列生成场景）

```python
# 在已有约束 c_i 中为新变量 x 指定系数 a_i
col = gp.Column()
for i, constr in enumerate(m.getConstrs()):
    col.addTerms(a[i], constr)
x_new = m.addVar(obj=c_new, column=col, name=f"x_new")
```

## 2. 约束创建的所有形式

### 2.1 单约束

```python
# 最基本
m.addConstr(expr1 <= expr2, name="c")

# 复合（表达式左右均可）
m.addConstr(3*x + y >= 2*z - 5)

# 范围约束 lhs <= expr <= rhs
m.addRange(expr, lhs, rhs, name="range")

# 等价写法（更繁琐）
m.addConstr(expr >= lhs)
m.addConstr(expr <= rhs)
```

### 2.2 批量 `addConstrs`

```python
# 生成器表达式返回 tupledict
cons = m.addConstrs((x[i] + y[i] == 1 for i in I), name="c")
# cons[i] 即第 i 条约束

# 多重索引
m.addConstrs((x[i,j] <= c[i,j] for i in I for j in J), name="cap")
```

### 2.3 一般约束

```python
# MAX / MIN
m.addGenConstrMax(resvar, vars, constant=0.0, name="")
m.addGenConstrMin(resvar, vars, constant=0.0, name="")

# ABS（单变量）
m.addGenConstrAbs(resvar, argvar, name="")

# AND / OR（变量必须为二进制）
m.addGenConstrAnd(resvar, argvars, name="")
m.addGenConstrOr(resvar, argvars, name="")

# Norm (0/1/2/inf)
m.addGenConstrNorm(resvar, argvars, which=2, name="")

# Indicator: 若 binvar == binval 则 expr 满足 sense rhs
m.addGenConstrIndicator(binvar, binval, expr, sense=None, rhs=None, name="")
# sense 和 rhs 通常从 expr 中推导：
m.addGenConstrIndicator(b, True, x + y <= 10)

# 或等价语法糖
m.addConstr((b == 1) >> (x + y <= 10))

# PWL: y = f(x) 分段线性
m.addGenConstrPWL(x, y, xpts, ypts, name="")

# 非线性约束 (13.0)
m.addGenConstrNL(y, opcode, data, parent, name="")
# Python 用户通常通过 addConstr(y == nlfunc.exp(x)) 自动生成
```

## 3. 特殊表达式构造

### 3.1 LinExpr

```python
# 创建
expr = gp.LinExpr()
expr.add(3, x)          # expr += 3*x
expr.addTerms(coefs, vars)   # 批量
expr.addConstant(5)

# 从 numpy 数组
expr = gp.LinExpr(coef_array, var_list)

# 查询
for coef, var in expr.linTerms():    # 13.0 新
    print(coef, var)

size = expr.size()                    # 项数
coef_i = expr.getCoeff(i)
var_i  = expr.getVar(i)
const  = expr.getConstant()
value  = expr.getValue()              # 当前解下表达式的值
```

### 3.2 QuadExpr

```python
q = x*x + 2*x*y + y*y + 3*x - 1
q.size()                              # 二次项数
q.getCoeff(i)
q.getVar1(i), q.getVar2(i)
q.getLinExpr()                        # 线性部分

# 13.0
for coef, v1, v2 in q.quadTerms():
    print(coef, v1, v2)
for coef, v in q.linTerms():
    print(coef, v)
```

### 3.3 GenExpr / NLExpr (13.0)

```python
from gurobipy import nlfunc
expr = nlfunc.exp(x) + nlfunc.sin(x*y)   # NLExpr
# 不支持 getValue() 等查询（符号式）
```

## 4. tupledict 高级用法

```python
x = m.addVars(I, J, name="x")   # tupledict

# 部分索引查询
x.sum(i, '*')           # sum over j
x.sum('*', j)           # sum over i
x.sum(i, '*', '*')      # 三维切片

# 按权重求和
x.prod(c, i, '*')       # sum c[i,j] * x[i,j] over j

# 取子集
sub = x.select(i, '*')  # list of vars
x.subset(I_sub, J_sub)  # 新 tupledict

# 迭代
for (i,j), var in x.items():
    ...

# 转为 numpy 数组（若是矩阵索引）
import numpy as np
arr = np.array([[x[i,j].X for j in J] for i in I])
```

## 5. MVar（矩阵变量）完整 API

```python
import numpy as np
from scipy import sparse

# 创建
X = m.addMVar(shape=(3, 4), lb=0, vtype=GRB.CONTINUOUS, name="X")

# 形状
X.shape       # (3, 4)
X.size        # 12
X.ndim        # 2

# 运算
Y = 2 * X + 1                          # MLinExpr
quad = X @ Q @ X.T                     # MQuadExpr
expr = A @ X + b                       # 矩阵乘法

# 约束
m.addConstr(A @ x == b)                # 矩阵约束
m.addConstr(X.sum(axis=0) <= cap)      # 按行求和
m.addConstr(X.sum(axis=1) >= demand)   # 按列求和

# 索引
X[i, j]                 # MVar（标量）
X[i, :]                 # 行
X[:, j]                 # 列
X[mask]                 # 布尔索引

# 属性
X.X                     # ndarray 形状 (3,4)
X.LB / X.UB            # ndarray

# 设置
X.LB = 0
X[i, j].UB = 10

# 迭代
for i in range(X.shape[0]):
    for j in range(X.shape[1]):
        var_ij = X[i,j]    # 仍是 MVar

# 从/到稀疏
mat = sparse.csr_matrix(...)
m.addConstr(mat @ x <= b)
```

## 6. 模型属性和参数的批量访问（13.0）

13.0 起 `getAttr` 和 `setAttr` 可以直接传 Var/Constr 对象数组或字符串名：

```python
# 传统方式
for v in m.getVars():
    v.LB = 0
    print(v.X)

# 批量（更快）
vars_list = m.getVars()
m.setAttr("LB", vars_list, [0.0] * len(vars_list))

x_vals = m.getAttr("X", vars_list)        # list of floats
names = m.getAttr("VarName", vars_list)

# 13.0 无需传 model 即可获取数组属性
m.getAttr(GRB.Attr.X)                     # 所有变量的 X
```

## 7. Model 的生命周期方法

```python
# 创建
m = gp.Model("name")                      # 用默认 env
m = gp.Model(env=env, name="...")

# 更新（同步延迟添加的对象）
m.update()

# 复制
m2 = m.copy()                             # 深拷贝

# 修正为可行
m.fixed()                                 # 返回固定 MIP 变量后的 LP 模型

# 预处理后的模型
p = m.presolve()

# 重置
m.reset()                                 # 清除解，保留模型
m.reset(0)                                # 仅重置求解状态
m.reset(1)                                # 同时重置 MIP starts
m.remove(obj)                             # 删除变量/约束/目标

# 销毁
m.dispose()                               # 或用 with 语句自动管理
```

## 8. 环境管理

```python
# 显式环境
env = gp.Env()

# 空环境 + 参数
env = gp.Env(empty=True)
env.setParam("OutputFlag", 0)
env.setParam("LogFile", "gurobi.log")
env.start()

# 云许可证
params = {
    "CSManager": "http://server:61080",
    "UserName": "myuser",
    "ServerPassword": "mypass",
}
env = gp.Env(params=params)

# 本地与 token 服务器
params = {"TokenServer": "license-server.company.com"}
env = gp.Env(params=params)

# 上下文管理（推荐）
with gp.Env() as env, gp.Model(env=env) as m:
    # ...
    pass
# 自动调用 env.dispose() 和 m.dispose()
```

## 9. 回调 cbGet 常量全表 (Python)

```python
# POLLING: 无可查
# PRESOLVE
GRB.Callback.PRE_COLDEL      # 已删除列数
GRB.Callback.PRE_ROWDEL      # 已删除行数
GRB.Callback.PRE_SENCHG      # sense 改变数
GRB.Callback.PRE_BNDCHG      # 边界改变数
GRB.Callback.PRE_COECHG      # 系数改变数

# SIMPLEX
GRB.Callback.SPX_ITRCNT      # 迭代数
GRB.Callback.SPX_OBJVAL
GRB.Callback.SPX_PRIMINF
GRB.Callback.SPX_DUALINF
GRB.Callback.SPX_ISPERT      # 是否扰动 (0/1/2)

# BARRIER
GRB.Callback.BARRIER_ITRCNT
GRB.Callback.BARRIER_PRIMOBJ / DUALOBJ
GRB.Callback.BARRIER_PRIMINF / DUALINF
GRB.Callback.BARRIER_COMPL

# MIP
GRB.Callback.MIP_OBJBST      # 最优可行解
GRB.Callback.MIP_OBJBND      # 最优下界
GRB.Callback.MIP_NODCNT      # 节点数
GRB.Callback.MIP_SOLCNT
GRB.Callback.MIP_CUTCNT
GRB.Callback.MIP_NODLFT      # 剩余节点
GRB.Callback.MIP_ITRCNT      # 单纯形迭代总数
GRB.Callback.MIP_OPENSCENARIOS

# MIPSOL
GRB.Callback.MIPSOL_SOL      # 解向量 (需 cbGetSolution)
GRB.Callback.MIPSOL_OBJ
GRB.Callback.MIPSOL_OBJBST / OBJBND
GRB.Callback.MIPSOL_NODCNT / SOLCNT

# MIPNODE
GRB.Callback.MIPNODE_STATUS  # 节点 LP 状态
GRB.Callback.MIPNODE_REL     # 松弛解 (需 cbGetNodeRel)
GRB.Callback.MIPNODE_OBJBST / OBJBND / NODCNT / SOLCNT

# MESSAGE
GRB.Callback.MSG_STRING

# MULTIOBJ
GRB.Callback.MULTIOBJ_OBJCNT
GRB.Callback.MULTIOBJ_SOLCNT
GRB.Callback.MULTIOBJ_SOL

# IIS
GRB.Callback.IIS_CONSTRMIN/MAX/GUESS
GRB.Callback.IIS_BOUNDMIN/MAX/GUESS
```

## 10. 日志重定向

```python
# 关闭所有日志
m.Params.OutputFlag = 0

# 只写文件
m.Params.LogToConsole = 0
m.Params.LogFile = "solve.log"

# 自定义日志（捕获每行）
def log_cb(model, where):
    if where == GRB.Callback.MESSAGE:
        msg = model.cbGet(GRB.Callback.MSG_STRING)
        my_logger.info(msg.rstrip())
m.optimize(log_cb)

# 切换日志文件
m.Params.LogFile = "new_log.log"
```

## 11. 暖启动（MIP Start）

```python
# 方式 1：Start 属性
for v in m.getVars():
    v.Start = my_heuristic_sol[v.VarName]

# 方式 2：从文件
m.read("init.mst")

# 方式 3：设置部分变量（其他由 Gurobi 补全）
x[1].Start = 1.0
x[2].Start = 0.0
# 其他 Start 保持默认 undefined

# 13.0 新：运行 MIP start 的时间和工作限制
m.Params.StartTimeLimit = 30
m.Params.StartWorkLimit = 1000
```

## 12. 解池 (Solution Pool)

```python
m.Params.PoolSearchMode = 2    # 2 = 寻找前 N 个解
m.Params.PoolSolutions = 10
m.Params.PoolGap = 0.1          # 只保留 10% gap 内的

m.optimize()

for k in range(m.SolCount):
    m.Params.SolutionNumber = k
    print(f"Sol {k}: obj = {m.PoolObjVal}")   # 13.0 起: m.PoolNObjVal
    for v in m.getVars():
        print(f"  {v.VarName} = {v.Xn}")      # 13.0 起: v.PoolNX
```

## 13. 多场景（multi-scenario）

批量处理同一模型的多组参数（如不同需求量、容量等）：

```python
m.NumScenarios = 3

# 场景 0：原始参数（默认）
m.Params.ScenarioNumber = 0
m.ScenNName = "baseline"

# 场景 1：修改某变量的上界
m.Params.ScenarioNumber = 1
m.ScenNName = "scenario_1"
x[0].ScenNUB = 50                   # 该场景下 x[0] 上界
c1.ScenNRHS = 100                   # 该场景下约束 c1 右端

# 场景 2：修改目标系数
m.Params.ScenarioNumber = 2
x[0].ScenNObj = 10

m.optimize()

# 查询各场景结果
for s in range(m.NumScenarios):
    m.Params.ScenarioNumber = s
    print(f"{m.ScenNName}: obj = {m.ScenNObjVal}")
```

## 14. 批量求解 (Batch Mode)

用于 Cluster Manager 部署：
```python
env = gp.Env(params={"CSManager": "..."})
batch = env.createBatch()
batch.writeMPS(...)
batch.submit()
batch_id = batch.ID
# ... 稍后查询
batch = env.getBatch(batch_id)
status = batch.BatchStatus
if status == GRB.BATCH_COMPLETED:
    batch.retry()  # 或 getJSONSolution()
```

## 15. 常见性能陷阱与技巧

### 慢：

```python
# 反例 1：Python sum 超慢
expr = sum(c[i] * x[i] for i in range(10000))  # O(n²)

# 反例 2：逐个 addConstr
for i in range(10000):
    m.addConstr(x[i] + y[i] <= z[i])

# 反例 3：lambda 中不使用 tupledict
m.addConstrs(
    (gp.quicksum(x[i,j] for j in J if cond[i,j]) <= 1
     for i in I)
)
# 更快：预先组织好索引
```

### 快：

```python
# quicksum 线性
expr = gp.quicksum(c[i] * x[i] for i in range(10000))

# addConstrs 批量
m.addConstrs((x[i] + y[i] <= z[i] for i in range(10000)), name="c")

# tupledict.sum / prod
m.addConstr(x.sum('*', j) <= 1)
m.addConstr(x.prod(cost, i, '*') <= budget)

# MVar + numpy
m.addConstr(A @ x <= b)
```

### 其他最佳实践：

```python
# 1. 一次 update()，不要每次添加都更新
# Gurobi 的默认 UpdateMode=1 通常不需显式 update()

# 2. 避免 m.getVars() 在循环中
vars = m.getVars()   # 只查一次
for v in vars: ...

# 3. 解冻 X / RC / Pi 等属性是 O(1)，但数组访问更快
X = m.getAttr("X", vars)    # list

# 4. 大规模 MIP 关闭输出减少 I/O
m.Params.OutputFlag = 0
# 自定义回调打印需要的信息

# 5. 使用 environment variable 做许可证配置，不要硬编码
import os
os.environ["GRB_LICENSE_FILE"] = "/path/to/gurobi.lic"
```
