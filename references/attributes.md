# Gurobi 属性速查

属性分为三类：**模型属性 (Model)**、**变量属性 (Var)**、**约束属性 (Constr/QConstr/GenConstr/SOS)**。
读写方式：`obj.AttrName` 或 `obj.getAttr("AttrName")` / `obj.setAttr("AttrName", val)`。

## 模型属性

### 优化状态

| 属性 | 类型 | 说明 |
|------|------|------|
| **`Status`** | INT | 求解状态码（下表） |
| **`ObjVal`** | DBL | 当前目标值 |
| `ObjBound` | DBL | 目标下界（MIP） |
| `ObjBoundC` | DBL | 未经过 epsilon 变换的下界 |
| `MIPGap` | DBL | 当前相对差距 |
| `Runtime` | DBL | 上次 optimize 墙钟时间 |
| `Work` | DBL | 上次 optimize 工作量 |
| `IterCount` | DBL | 单纯形迭代次数 |
| `BarIterCount` | INT | 内点法迭代 |
| `NLBarIterCount` (13.0) | - | NL barrier 迭代 |
| `PDHGIterCount` (13.0) | - | PDHG 迭代 |
| `NodeCount` | DBL | MIP 分支节点 |
| `BarStatus` (13.0) | - | barrier 交叉前的解状态 |
| `SolCount` | INT | 解池中的解数 |

### 状态码 (Status)

| 值 | 常量 | 含义 |
|----|------|------|
| 1 | `LOADED` | 已加载未求解 |
| 2 | `OPTIMAL` | 找到最优 |
| 3 | `INFEASIBLE` | 不可行 |
| 4 | `INF_OR_UNBD` | 不可行或无界（跑完后可设 `DualReductions=0` 区分） |
| 5 | `UNBOUNDED` | 无界 |
| 6 | `CUTOFF` | Cutoff 界内无解 |
| 7 | `ITERATION_LIMIT` | 到达迭代上限 |
| 8 | `NODE_LIMIT` | 到达节点上限 |
| 9 | `TIME_LIMIT` | 到达时间上限 |
| 10 | `SOLUTION_LIMIT` | 到达解数上限 |
| 11 | `INTERRUPTED` | 用户中断 |
| 12 | `NUMERIC` | 数值错误 |
| 13 | `SUBOPTIMAL` | 次优 |
| 14 | `INPROGRESS` | 异步中 |
| 15 | `USER_OBJ_LIMIT` | 达 BestObjStop/BestBdStop |
| 16 | `WORK_LIMIT` | 工作上限 |
| 17 | `MEM_LIMIT` | 内存上限（soft） |
| 18 | `LOCALLY_SOLVED` (13.0) | NL barrier 局部最优 |
| 19 | `LOCALLY_INFEASIBLE` (13.0) | NL 局部不可行 |

### 模型结构

| 属性 | 说明 |
|------|------|
| `NumVars` | 变量数 |
| `NumConstrs` | 线性约束数 |
| `NumSOS` | SOS 约束数 |
| `NumQConstrs` | 二次约束数 |
| `NumGenConstrs` | 一般约束数 |
| `NumNLConstrs` | 非线性约束数 |
| `NumNZs` | 非零系数数 |
| `NumQNZs` | 二次非零 |
| `NumIntVars` | 整数变量数 |
| `NumBinVars` | 二进制变量数 |
| `ModelSense` | 1=最小，-1=最大 |
| `ModelName` | 名称 |
| `IsMIP` | 是否 MIP |
| `IsQP` | 是否 QP |
| `IsQCP` | 是否 QCP |
| `IsMultiObj` | 是否多目标 |

### 多目标

| 属性 | 说明 |
|------|------|
| `NumObj` | 目标数 |
| `ObjNumber` | 当前查询的目标索引（参数） |
| `ObjNCon`, `ObjNVal`, `ObjNPriority`, `ObjNWeight`, `ObjNRelTol`, `ObjNAbsTol`, `ObjNName` | 各目标的属性 |
| `NumObjPasses` (13.0) | 多目标扫描遍数 |
| `ObjPassN*` (13.0) | 每遍的 ObjVal/ObjBound/NodeCount/Runtime/Status 等 |

## 变量属性

### 解信息

| 属性 | 说明 |
|------|------|
| **`X`** | 变量当前解 |
| `Xn` (13.0 已弃用) | 解池第 n 个解——改用 `PoolNX` |
| `PoolNX` (13.0) | 解池第 n 个解（`ObjNumber` 参数控制 n） |
| `RC` | 简约成本（LP） |
| `BarX` | barrier 的未交叉解 |
| `UnbdRay` | 无界射线（LP 无界时） |
| `Start` | MIP start 值 |
| `VarHintVal`, `VarHintPri` | 用户提示值/优先级 |
| `BranchPriority` | 分支优先级 |

### 定义

| 属性 | 说明 |
|------|------|
| `LB`, `UB` | 边界 |
| `Obj` | 线性目标系数 |
| `VType` | 'C'/'B'/'I'/'S'/'N'（C/B/I/SEMICONT/SEMIINT） |
| `VarName` | 名称 |
| `VBasis` | 0=basic, -1=lb, -2=ub, -3=super basic |
| `SAObjLow`, `SAObjUp`, `SALBLow`, `SALBUp`, `SAUBLow`, `SAUBUp` | 灵敏度范围（LP） |

### 特殊

| 属性 | 说明 |
|------|------|
| `IISLB`, `IISUB`, `IISLBForce`, `IISUBForce` | IIS 成员关系 |
| `PreFixVal` | 预处理时固定值 |
| `PartitionNumber` | 分区启发式 |

## 约束属性

### 线性约束 (LinConstr)

| 属性 | 说明 |
|------|------|
| **`Pi`** | 对偶变量（LP） |
| **`Slack`** | 松弛 |
| `RHS` | 右端 |
| `Sense` | '<'/'='/'>' |
| `ConstrName` | 名称 |
| `CBasis` | 基状态 |
| `IISConstr`, `IISConstrForce` | IIS 成员 |
| `FarkasDual` | 不可行证明（LP 不可行时） |
| `Lazy` | 0/1/2/3 惰性级别 |
| `DStart` | 对偶起始 |
| `SARHSLow`, `SARHSUp` | 灵敏度 |

### 二次约束 (QConstr)

`QCRHS`, `QCSense`, `QCName`, `QCPi`（QCP 对偶），`QCSlack`。

### 一般约束 (GenConstr)

`GenConstrName`, `GenConstrType`（MAX/MIN/ABS/AND/OR/NORM/INDICATOR/PWL/POLY/EXP/LOG/POW/SIN/COS/TAN/LOGISTIC/NL）。

| 相关属性 | 说明 |
|------|------|
| `FuncPieces` | PWL 近似段数 |
| `FuncPieceLength` | 段长 |
| `FuncPieceError` | 允许误差 |
| `FuncPieceRatio` | 高估/低估比 |
| `FuncNonlinear` | 1=空间 B&B，0=静态 PWL |
| `FuncMaxVal` | 函数约束 x/y 最大值 |

### 非线性约束

类似 GenConstr，通过 `m.getGenConstrNL(gc)` 获取表达式树，通过 `m.addGenConstrNL()` 添加。

## 解池属性（13.0 新命名）

| 属性 | 含义 |
|------|------|
| `PoolSolutions` | 设置保留解数 |
| `SolCount` | 实际解数 |
| `ObjNumber` / `SolutionNumber` | 参数：查询第几个解 |
| `PoolNX` | 第 n 解的变量值（原 `Xn`） |
| `PoolNObjVal` | 第 n 解的目标（原 `PoolObjVal`） |
| `PoolNMaxVio` | 第 n 解最大违反（13.0 新） |
| `PoolNBoundVio`, `PoolNBoundVioIndex`, `PoolNBoundVioSum` | 边界违反 |
| `PoolNConstrVio`, `PoolNConstrVioIndex`, `PoolNConstrVioSum` | 约束违反 |
| `PoolNIntVio`, `PoolNIntVioIndex`, `PoolNIntVioSum` | 整数违反 |

## 常用代码片段

```python
# 求解后安全取解
m.optimize()
if m.Status == GRB.OPTIMAL:
    for v in m.getVars():
        print(f"{v.VarName} = {v.X}")
elif m.Status == GRB.INFEASIBLE:
    print("不可行，计算 IIS")
    m.computeIIS()
    m.write("iis.ilp")
elif m.Status == GRB.UNBOUNDED:
    m.Params.InfUnbdInfo = 1
    m.optimize()
    for v in m.getVars():
        if v.UnbdRay != 0:
            print(f"Unbounded ray {v.VarName} = {v.UnbdRay}")

# 查询灵敏度（LP）
for v in m.getVars():
    print(f"{v.VarName}: RC={v.RC:.3f}, obj range=[{v.SAObjLow:.2f}, {v.SAObjUp:.2f}]")

# 解池
m.Params.PoolSearchMode = 2
m.Params.PoolSolutions = 10
m.optimize()
for k in range(m.SolCount):
    m.Params.SolutionNumber = k
    print(f"Sol {k}: obj={m.PoolObjVal:.3f}")
    for v in m.getVars():
        print(f"  {v.VarName} = {v.Xn}")   # 13.0 之前
        # 13.0+: v.PoolNX
```
