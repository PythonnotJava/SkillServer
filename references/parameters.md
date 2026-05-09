# Gurobi 参数详解与调优指南

Gurobi 约 200+ 个参数。**默认值通常是最优选择**；只在有明确理由时修改。

## 设置参数的方法

```python
# Python
m.Params.TimeLimit = 60
m.setParam("MIPGap", 0.01)

# 命令行
gurobi_cl TimeLimit=60 MIPGap=0.01 model.mps

# 参数文件 .prm
m.read("config.prm")
m.write("config.prm")
```

参数名**大小写和下划线不敏感**：`TimeLimit`、`TIMELIMIT`、`TIME_LIMIT` 等效。

## 参数分组

### 1. 终止参数 (Termination)

设定停止条件。

| 参数 | 默认 | 说明 |
|------|------|------|
| **`TimeLimit`** | ∞ | 墙钟时间上限（秒）——最常用 |
| **`WorkLimit`** | ∞ | 确定性工作单位上限（≈ 秒但与硬件无关） |
| **`MIPGap`** | 1e-4 | MIP 相对差距，达到即停 |
| **`MIPGapAbs`** | 1e-10 | 绝对差距 |
| `SolutionLimit` | ∞ | 找到 N 个可行解即停 |
| `NodeLimit` | ∞ | MIP 节点上限 |
| `IterationLimit` | ∞ | 单纯形迭代上限 |
| `BarIterLimit` | 1000 | 内点法迭代上限 |
| `NLBarIterLimit` (13.0) | - | NL 内点法迭代 |
| `PDHGIterLimit` (13.0) | - | PDHG 迭代 |
| `BestBdStop` | | 界好于此值即停 |
| `BestObjStop` | | 解好于此值即停 |
| `Cutoff` | | 目标截断值 |
| `MemLimit` | ∞ | 内存上限 (GB)，超出则 OUT_OF_MEMORY |
| `SoftMemLimit` | ∞ | 内存软限，可稍微超出但会优雅终止 |

### 2. 容差参数 (Tolerances)

| 参数 | 默认 | 说明 |
|------|------|------|
| `FeasibilityTol` | 1e-6 | 原始可行容差 |
| `OptimalityTol` | 1e-6 | 对偶可行容差 |
| `IntFeasTol` | 1e-5 | 整数可行容差 |
| `BarConvTol` | 1e-8 | 内点法收敛容差 |
| `BarQCPConvTol` | 1e-6 | QCP 内点收敛 |
| `MarkowitzTol` | 1e-4 | 单纯形主元 Markowitz 阈值 |
| `PSDTol` | 1e-6 | 半正定判定容差 |

### 3. 日志 (Logging)

| 参数 | 说明 |
|------|------|
| `OutputFlag` | 0=关闭所有输出，1=开 |
| `LogFile` | 日志文件名 |
| `LogToConsole` | 控制台日志开关 |
| `DisplayInterval` | 日志输出频率（秒） |

### 4. 预处理 (Presolve)

| 参数 | 说明 |
|------|------|
| `Presolve` | -1/0/1/2 = auto/off/conservative/aggressive |
| `PrePasses` | 预处理遍数上限 |
| `Aggregate` | 行聚合控制（0=off） |
| `PreSparsify` | 稀疏化 |
| `PreQLinearize` | Q 矩阵线性化 |
| `PreCrush` | 允许把原模型约束传递给 presolved 模型（callback 需要） |
| `PreSOS1BigM`, `PreSOS2BigM` | SOS 重构时允许的最大 bigM |

### 5. 单纯形 (Simplex)

| 参数 | 说明 |
|------|------|
| `Method` | -1=concurrent, 0=primal, 1=dual, 2=barrier, 3=concurrent, 4=deterministic, 5=PDHG (13.0), 6=NL barrier (13.0) |
| `Sifting` | sifting 算法级别 |
| `SiftMethod` | sift 子问题求解方法 |
| `SimplexPricing` | 定价策略 |
| `NormAdjust` | 定价范数 |
| `Quad` | 强制/禁用四倍精度 |
| `PerturbValue` | 扰动幅度 |

### 6. 内点法 (Barrier)

| 参数 | 说明 |
|------|------|
| `BarCorrectors` | 中心修正次数 |
| `BarOrder` | -1=auto, 0=AMD, 1=Nested Dissection |
| `BarHomogeneous` | 齐次内点法（诊断不可行/无界更强） |
| `Crossover` | -1=auto, 0=off, 1-4=不同初始基构造策略 |
| `CrossoverBasis` | 初始基策略 |
| `QCPDual` | 计算 QCP 对偶 |

### 7. MIP 控制

**最重要的两个参数**：

- **`Threads`**：线程数。默认 0 = 自动（最多 32）；13.0 起 `-1` = 使用全部虚拟核。
- **`MIPFocus`**：
  - `0`（默认）：平衡找可行解和证最优
  - `1`：找可行解优先
  - `2`：证最优优先
  - `3`：改进下界（bound）优先

| 参数 | 说明 |
|------|------|
| `BranchDir` | 分支方向偏好（-1/0/1） |
| `Heuristics` | 启发式时间占比（0~1） |
| `NoRelHeurTime/Work` | NoRel 启发式时间 |
| `NoRelHeurSolutions` (13.0) | NoRel 找到 N 个解即停 |
| `Symmetry` | 对称检测 |
| `RINS` | RINS 启发式频率 |
| `ImproveStartTime/Gap/Work/Nodes` | 切换到"改进阶段"的触发 |
| `StartTimeLimit/WorkLimit` (13.0) | MIP start 的子 MIP 限制 |
| `VarBranch` | 分支变量选择策略 |
| `IntegralityFocus` | 0/1，1=避免"trickle flow"等整数微违反 |
| `NonConvex` | -1/0/1/2，2=接受非凸二次 |
| `MIQCPMethod` | MIQCP 求解方法 |
| `NLPHeur` | 非凸二次 NLP 启发式 |
| `LazyConstraints` | 使用 lazy 回调必须设为 1 |
| `PreCrush` | 添加用户割必须设为 1 |
| `NodefileStart` | 超过 N GB 把节点写盘 |
| `NodefileDir` | 节点文件目录 |

### 8. 割平面 (Cuts)

`Cuts` 全局控制：-1=auto, 0=off, 1=conservative, 2=aggressive, 3=very aggressive。

各具体割也可独立控制：`CliqueCuts`, `CoverCuts`, `FlowCoverCuts`, `FlowPathCuts`, `GomoryPasses`, `GUBCoverCuts`, `ImpliedCuts`, `InfProofCuts`, `LiftProjectCuts`, `MIRCuts`, `MixingCuts`, `ModKCuts`, `NetworkCuts`, `PSDCuts`, `RelaxLiftCuts`, `RLTCuts`, `StrongCGCuts`, `SubMIPCuts`, `ZeroHalfCuts`, `BQPCuts`, `MasterKnapsackCuts`（13.0 新）, `DualImpliedCuts`, `ProjImpliedCuts`, `MIPSepCuts`。

### 9. 数值 (Numerics)

| 参数 | 说明 |
|------|------|
| `NumericFocus` | 0/1/2/3，越高越保守但越慢 |
| `IntegralityFocus` | 严格整数性 |
| `BarHomogeneous` | 诊断数值 |
| `ObjScale` | 目标缩放 |
| `ScaleFlag` | -1/0/1/2/3，模型缩放方法 |

### 10. 求解池 (Solution Pool)

| 参数 | 说明 |
|------|------|
| `PoolSolutions` | 保留解数量 |
| `PoolGap` | 相对差距，超出不保留 |
| `PoolGapAbs` | 绝对差距 |
| `PoolSearchMode` | 0=无保证，1=部分，2=搜索前 N 个 |

### 11. 多目标

| 参数 | 说明 |
|------|------|
| `ObjNumber` | 查询属性时的目标索引 |
| `MultiObjMethod` | 子问题 warm start |
| `MultiObjPre` | 多目标预处理级别 |
| `MultiObjSettings` | 从 .prm 加载每个目标的设置 |

### 12. Tuner

| 参数 | 说明 |
|------|------|
| `TuneCriterion` | 调优指标 |
| `TuneTimeLimit` | 调优总时间 |
| `TuneTrials` | 每组参数试多少次 |
| `TuneIgnoreSettings` (13.0) | 跳过某些参数 |
| `TuneResults` | 返回多少组 |
| `TuneTargetMIPGap/TargetTime` | 目标差距/时间 |
| `TuneJobs`/`TuneDynamicJobs` | 分布式调优 |

## 参数选择指南

### 连续模型 (LP/QP)

- `Method`：默认 -1 对 LP 用并发，对 QP 用并行 barrier。内存紧张改为 `Method=1` (dual simplex)。
- QCP/SOCP 只能用 barrier (`Method=2`)。
- 想要确定性结果：`Method=4`。
- **PDHG** (13.0)：大规模 LP 尝试 `Method=5`（`PDHGGPU=1` 可用 NVIDIA GPU 加速，beta）。
- 不可行/无界诊断：`BarHomogeneous=1` + `InfUnbdInfo=1`。

### MIP 模型

**关键参数优先级**：
1. **`Threads`** 设为实际核数
2. **`MIPFocus`** 按需求选 1/2/3
3. **`TimeLimit`** 设合理上限
4. **`MIPGap`** 放宽到业务可接受水平（默认 0.01%，很多实际问题设 1% 就够）

**MIP 太慢**按顺序试：
1. 改 `MIPFocus`
2. 内存大模型：`NodefileStart=0.5`
3. 启发式强化：`Heuristics=0.5` 或 `MIPFocus=1`
4. 诊断：`NoRelHeurTime=60`（不解松弛直接启发式找解）
5. `Model.tune()`

**证明最优慢**：
- `MIPFocus=3` 改进 bound
- 割更激进：`Cuts=2`
- `Symmetry=2`

**根松弛解太慢**：
- 换根算法 `Method=2/3`
- 减少预处理 `Presolve=1` 或甚至 `0`

### 数值困难

- 默认 `NumericFocus=0` 最快；数值问题时逐步提高到 1→2→3。
- 大系数（> 1e6）或小系数（< 1e-3）导致的病态模型应重新缩放建模。
- "Trickle flow"（整数微违反导致错答）：`IntegralityFocus=1`，代价 ~5-10% 性能。

### 内存紧张

1. `Threads` 调小（每线程复制一份模型）
2. `NodefileStart=0.5`（写盘）
3. `Method=1`（dual simplex，不需要 barrier 的因子分解）
4. `MemLimit`/`SoftMemLimit` 设硬/软限

## 调用 Tuner

```python
m = gp.read("hard.mps")
m.Params.TuneTimeLimit = 3600
m.Params.TuneTrials = 3
m.tune()
m.getTuneResult(0)   # 应用最佳
m.write("best.prm")
m.optimize()
```

Tuner 不适合"全局搜索最佳参数"——它只尝试 Gurobi 认为有希望的组合。对 LP 模型通常帮助有限。

## 可回调设置的参数

以下参数支持 callback 中运行时修改（通过 `cbSetParam`）：
- `TimeLimit`
- `WorkLimit`
- `NodeLimit`
- `BarIterLimit`
- `PumpPasses`

典型用法：动态时间限制（找到首个可行解后给 X 秒证最优）。
