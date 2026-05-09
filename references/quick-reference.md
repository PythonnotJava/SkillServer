# Gurobi 速查卡

## 常用 import

```python
import gurobipy as gp
from gurobipy import GRB, quicksum, nlfunc
```

## 变量类型常量

| Python | 含义 |
|--------|------|
| `GRB.CONTINUOUS` | 'C' 连续 |
| `GRB.BINARY` | 'B' 二进制 |
| `GRB.INTEGER` | 'I' 整数 |
| `GRB.SEMICONT` | 'S' 半连续 |
| `GRB.SEMIINT` | 'N' 半整数 |

## 目标方向

```python
GRB.MINIMIZE  #  1
GRB.MAXIMIZE  # -1
```

## 约束比较符

`<=`, `>=`, `==` （不支持 `<`, `>`, `!=`）

## 常用属性

```python
m.Status         # 状态码
m.ObjVal         # 目标值
m.ObjBound       # MIP 下界
m.MIPGap         # 相对差距
m.Runtime        # 时间
m.IterCount      # 单纯形迭代
m.NodeCount      # MIP 节点
m.SolCount       # 解池大小

v.X              # 变量值
v.RC             # 简约成本 (LP)
v.LB / v.UB      # 边界

c.Pi             # 对偶变量 (LP)
c.Slack          # 松弛
c.RHS            # 右端
```

## 常用状态

```python
GRB.OPTIMAL              # 2
GRB.INFEASIBLE           # 3
GRB.INF_OR_UNBD          # 4
GRB.UNBOUNDED            # 5
GRB.TIME_LIMIT           # 9
GRB.INTERRUPTED          # 11
GRB.SUBOPTIMAL           # 13
GRB.LOCALLY_OPTIMAL      # 18 (13.0 新)
GRB.LOCALLY_INFEASIBLE   # 19 (13.0 新)
```

## 常用参数

```python
m.Params.TimeLimit = 60
m.Params.MIPGap = 0.01
m.Params.Threads = 0          # -1 (13.0) = 全部虚拟核
m.Params.OutputFlag = 0
m.Params.LogFile = "out.log"

# MIP 策略
m.Params.MIPFocus = 1         # 找可行
m.Params.MIPFocus = 2         # 证最优
m.Params.MIPFocus = 3         # 改进下界

# 方法
m.Params.Method = -1          # 自动
m.Params.Method = 1           # 对偶单纯形（省内存）
m.Params.Method = 2           # 内点
m.Params.Method = 3           # 并发
m.Params.Method = 5           # PDHG (13.0)
m.Params.Method = 6           # NL barrier (13.0)

# 非凸
m.Params.NonConvex = 2

# 数值
m.Params.NumericFocus = 3
m.Params.IntegralityFocus = 1

# 不可行诊断
m.Params.DualReductions = 0    # 区分 inf/unbd
m.Params.InfUnbdInfo = 1       # 得到 FarkasDual/UnbdRay
m.Params.BarHomogeneous = 1    # barrier 诊断

# 回调
m.Params.LazyConstraints = 1   # 启用 lazy
m.Params.PreCrush = 1          # 启用 user cut

# 局部最优
m.Params.OptimalityTarget = 1  # NL barrier 局部最优
```

## 表达式

```python
# 线性
expr = 2*x + 3*y
expr = quicksum(c[i]*x[i] for i in I)    # 大求和用这个！

# 二次
q = x*x + 2*x*y + y*y

# 非线性 (13.0)
nlfunc.exp(x)
nlfunc.log(x)
nlfunc.sin(x)
nlfunc.cos(x)
nlfunc.tan(x)
nlfunc.tanh(x)          # 13.0 新
nlfunc.logistic(x)
nlfunc.sqrt(x)
nlfunc.pow(x, a)
nlfunc.signpow(x, a)    # 13.0 新: sign(x) * |x|^a
nlfunc.log2(x)
nlfunc.log10(x)
```

## 添加约束的语法糖

```python
# indicator: if b==1 then expr <= rhs
m.addConstr((b == 1) >> (x + y <= 10))

# range
m.addRange(x + y, 2, 10)

# 批量
m.addConstrs((x[i] + y[i] == 1 for i in I), name="c")

# 一般约束
m.addGenConstrMax(r, [x, y, z])
m.addGenConstrMin(r, [x, y, z])
m.addGenConstrAbs(r, x)
m.addGenConstrAnd(r, [b1, b2])
m.addGenConstrOr(r, [b1, b2])
m.addGenConstrNorm(r, [x, y, z], which=2)
m.addGenConstrIndicator(b, True, lhs <= rhs)
m.addGenConstrPWL(x, y, xpts, ypts)
```

## tupledict 切片

```python
x = m.addVars(I, J, name="x")       # tupledict

x.sum(i, '*')           # sum over j
x.sum('*', j)           # sum over i
x.prod(c, i, '*')       # sum c[i,j] * x[i,j] over j
x.select(i, '*')        # list of variables
```

## 回调关键常量

```python
# where
GRB.Callback.POLLING / PRESOLVE / SIMPLEX / BARRIER
GRB.Callback.MESSAGE
GRB.Callback.MIP        # 周期性
GRB.Callback.MIPSOL     # 新整数解
GRB.Callback.MIPNODE    # 节点处理
GRB.Callback.MULTIOBJ
GRB.Callback.IIS

# cbGet 常用
GRB.Callback.MIP_NODCNT / MIP_OBJBST / MIP_OBJBND / MIP_SOLCNT
GRB.Callback.MIPSOL_OBJ / MIPSOL_SOL
GRB.Callback.MIPNODE_STATUS / MIPNODE_REL

# 回调操作
model.cbGet(what)
model.cbGetSolution(vars)           # in MIPSOL
model.cbGetNodeRel(vars)            # in MIPNODE
model.cbLazy(constraint)            # 添加 lazy
model.cbCut(constraint)             # 添加 user cut
model.cbSetSolution(vars, vals)     # 注入启发式
model.cbUseSolution()
model.terminate()
```

## 读写文件

| 后缀 | 含义 |
|------|------|
| `.mps`, `.rew` | 标准格式（含解名字段） |
| `.lp`, `.rlp` | LP 可读格式 |
| `.ilp` | IIS 输出 |
| `.sol` | 解 |
| `.mst` | MIP start |
| `.bas` | 单纯形基 |
| `.attr` | 属性 |
| `.prm` | 参数 |
| `.json` | JSON 解 |

所有后缀支持 `.gz` / `.bz2` / `.7z` 压缩。

## 环境管理

```python
# 推荐模式：自动释放许可证
with gp.Env() as env, gp.Model(env=env) as m:
    ...

# 云 / 集群
env = gp.Env(params={"CSManager": "http://...", "UserName": "u", "ServerPassword": "p"})

# 空环境 + 再配置
env = gp.Env(empty=True)
env.setParam("LogFile", "out.log")
env.start()
```
