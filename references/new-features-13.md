# Gurobi 13.0 新特性与迁移指南

## 发布亮点

Gurobi 13.0 于 2026 年发布（13.0.0 + 13.0.1），主要改进：

- **全面性能提升**：MIP 和 MINLP 默认更快，无需调参
- **NL Barrier 方法**：对非线性连续模型求局部最优，通常比全局求解器快得多
- **PDHG 算法**：大规模 LP 的一阶方法，支持 NVIDIA GPU 加速（beta）
- **符号幂 / 双曲正切**：`signpow(x,a) = sign(x)·|x|^a`，`tanh(x)`

## 新特性详解

### 1. NL Barrier Method（非线性内点法，预览版）

为 NLP 问题（只含连续变量和非线性约束）寻找**局部最优**：

```python
import gurobipy as gp
from gurobipy import GRB, nlfunc

m = gp.Model()
x = m.addVar(lb=-10, ub=10, name="x")
y = m.addVar(lb=-10, ub=10, name="y")

m.addConstr(y == nlfunc.exp(x) + nlfunc.sin(x))
m.setObjective(x*x + y*y, GRB.MINIMIZE)

m.Params.OptimalityTarget = 1   # 启用局部最优模式
m.optimize()
# Status 将是 LOCALLY_OPTIMAL (18) 或 LOCALLY_INFEASIBLE (19)

print(f"NL barrier iters: {m.NLBarIterCount}")
```

控制参数：`NLBarIterLimit`, `NLBarCFeasTol`, `NLBarDFeasTol`, `NLBarPFeasTol`。

当模型**没有**离散元素（整数、SOS、PWL）并且全局求解器太慢时非常有用。**不保证全局最优**（除非模型凸）。

### 2. PDHG（原始-对偶混合梯度）

大规模 LP 的一阶方法：

```python
m.Params.Method = 6          # GRB_METHOD_PDHG
# m.Params.PDHGGPU = 1       # 如有 NVIDIA GPU（beta）
m.Params.PDHGConvTol = 1e-6
m.Params.PDHGAbsTol = 1e-6
m.Params.PDHGRelTol = 1e-6
m.optimize()
print("PDHG iters:", m.PDHGIterCount)
```

支持平台：Linux x86-64 / Linux arm64 + NVIDIA H100 或更新 GPU（CUDA 12/13）。

### 3. 非线性操作扩展

**新 OPCODE**：
- `OPCODE_TANH`：`tanh(x)`
- `OPCODE_SIGNPOW`：`signpow(x, a) = sign(x) · |x|^a`，其中 `a >= 1`

Python 中：
```python
from gurobipy import nlfunc
m.addConstr(y == nlfunc.tanh(x))
m.addConstr(z == nlfunc.signpow(x, 3))   # = x³ 当 x>=0，= -|x|³ 当 x<0
m.addConstr(w == nlfunc.signpow(x, 2))   # = x*|x|
```

### 4. NoRel 启发式增强

- `NoRelHeurSolutions`：找到指定数量的可行解后停止
- NoRel 现在利用用户提供的 `VarHintVal`

### 5. Callback 精细控制

所有 API 的回调都可指定只关心哪些 `where` 标志（减少远程调用开销）：

```python
# Python 13.0：
m.optimize(my_callback, wheres=[GRB.Callback.MIP, GRB.Callback.MIPSOL])
# 或
m.computeIIS(my_callback, wheres=[GRB.Callback.IIS])
```

### 6. Tuner 增强

- 支持 **MIP starts** 和 **branch priorities**（之前只能 MIP starts）
- `TuneIgnoreSettings`：跳过已测过的参数组合，支持中断后继续
- 调优回调：`tune()` 接受 callback，可从回调中 `terminate()`
- 每次 tune 结束会写 `tune-all.prm`

### 7. 线程设置新值

`Threads=-1`：使用机器所有虚拟处理器。`Threads=0`（默认）最多 32。

### 8. 其他改进

- `LPWarmStart` 默认改为 `-1`（自适应——PDHG 用 2，其他算法用 1）
- `ImproveStartWork` 新参数（配合 `ImproveStartTime`）
- `MasterKnapsackCuts` 新参数控制主背包割
- `FixVarsInIndicators` 新参数控制 `convertToFixed` 对指示约束的处理
- `NumObjPasses` 和 `ObjPassN*` 属性可查询多目标每次扫描的结果
- `BarStatus` 属性可查 barrier 交叉前状态

## Python (gurobipy) API 变化

### 新增

- `LinExpr.linTerms()`：迭代线性项 `(coef, var)`
- `QuadExpr.linTerms()`, `QuadExpr.quadTerms()`
- `Model.getQ()`, `Model.getQCMatrices()`：返回 `scipy.sparse` 表示
- `loadModel`：直接从数据构造 Model，不创建 Var/Constr 对象（高性能）
- `Model.getAttr()` / `setAttr()` 支持数组属性，无需传建模对象
- Windows Jupyter 中可优雅中断求解
- GIL 在 Env 启动时释放（多线程 Python 不再死锁）
- `Model.optimize(cb, wheres=...)`，`computeIIS(cb, wheres=...)`

### 行为变化

- `gp.setParam()` / `gp.resetParams()` 不再影响已创建的 Model 对象
- `Model.tune()` 支持 callback 终止

### 弃用（13.0 起发出警告，未来删除）

- **属性**：`Xn` → 改用 `PoolNX`；`PoolObjVal` → 改用 `PoolNObjVal`
- **Function Constraints**：`addGenConstrPoly/Exp/ExpA/Log/LogA/Logistic/Pow/Sin/Cos/Tan`
  - 以及对应的 `FuncPieceError/Length/Ratio/Pieces/Nonlinear`
  - 改用 **Nonlinear Constraints**（Python 的 `nlfunc` 辅助 / 表达式树）

### 移除

- `gurobipy.help()` — 用 Python 内置 `help()`
- `gurobipy.models()` — 移除
- `gurobipy.system()` — 用 `os.system`
- Interactive shell（`gurobi.sh`）— 改用 `from gurobipy import *`

## 其他 API 变化

### C++

- `GRBException` 现继承 `std::runtime_error`（可用 stdlib catch）

### MATLAB / R

- 解池字段 `xn` 改名为 `poolnx`

### JSON 解文件

- `Xn` → `PoolNX`，`PoolObjVal` → `PoolNObjVal`

### C API

- `GRBsetcallbackfuncadv`：带 wheres 过滤的回调

## 迁移清单（12 → 13）

1. **函数约束迁移**：
   ```python
   # 旧
   m.addGenConstrExp(x, y)
   # 新
   m.addConstr(y == nlfunc.exp(x))
   ```

2. **解池属性改名**：
   ```python
   # 旧
   for k in range(m.SolCount):
       m.Params.SolutionNumber = k
       val = x.Xn
       obj = m.PoolObjVal
   # 新
       val = x.PoolNX
       obj = m.PoolNObjVal
   ```

3. **捕获 deprecation 警告**：
   ```bash
   python -W default your_script.py
   # 或
   python -X dev your_script.py
   ```

4. **Remote Services 命令行标志**移除，改用对应参数名。

5. **交互式 shell** 移除，改写 Python 脚本。

## 支持的平台 (13.0.1)

| 平台 | 操作系统 | 编译器 |
|------|----------|--------|
| Windows 64-bit | Win 10 LTSC, 11, Server 2016-2025 | Visual Studio 2017-2026 |
| Linux x86-64 | RHEL 8/9/10, SUSE 15, Ubuntu 22.04/24.04, Amazon Linux 2023 | GCC ≥ 8.5 |
| macOS universal2 | macOS 14/15/26 (Sonoma / Sequoia / Tahoe) | Xcode 14/15/16 |
| Linux arm64 | RHEL 8/9/10, SUSE 15, Ubuntu 22.04/24.04, AL2023 | GCC ≥ 8.5 |

**语言版本**：Python 3.10-3.14（含 3.14t free-threading）、MATLAB R2019a-R2025a、R 4.5、JDK 8/11/17/21、.NET 8.0/10.0。

**GPU**：Linux x86-64 / arm64 + NVIDIA，建议 H100 或更新，CUDA 12/13。
