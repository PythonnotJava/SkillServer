# 多目标优化

Gurobi 只支持**多个线性目标**（非线性目标只能单一）。两种处理方式：

- **分层 (Hierarchical)**：按优先级依次优化，高优先级最优后才优化低优先级
- **混合 (Blended)**：加权组合为单个目标
- 两者可**混用**：相同优先级的目标合并（blended），不同优先级的依次（hierarchical）

## 设置多目标

```python
m.NumObj = 3

# 目标 0：成本（最高优先级）
m.setObjectiveN(cost_expr, index=0, priority=10, weight=1.0,
                abstol=0, reltol=0, name="cost")

# 目标 1：时间（次优先级）
m.setObjectiveN(time_expr, index=1, priority=5, weight=1.0,
                abstol=0, reltol=0.05, name="time")

# 目标 2 & 3：同优先级，加权合并
m.setObjectiveN(emissions_expr, index=2, priority=1, weight=2.0, name="emissions")
m.setObjectiveN(noise_expr, index=3, priority=1, weight=1.0, name="noise")

m.ModelSense = GRB.MINIMIZE   # 所有目标都最小化
m.optimize()
```

**参数说明**：
- `index`：目标编号 0..NumObj-1
- `priority`：越高越优先（分层）
- `weight`：同层内的加权
- `abstol`：允许下层目标使上层目标恶化的绝对量
- `reltol`：允许下层目标使上层目标恶化的相对量（%）
- `name`：可选名称

## 允许退化 (Degradation)

分层优化的关键细节：求解完第一个目标后，Gurobi 会**固定第一个目标不更差**（通过添加约束）再求解下一个。`abstol`/`reltol` 控制这个"不更差"的松紧：

- `abstol=0, reltol=0`：严格最优（默认）— 可能让后续目标无可行解
- `reltol=0.01`：允许前置目标恶化 1%
- `abstol=5`：允许恶化 5 个单位

## 查询结果

```python
if m.Status == GRB.OPTIMAL:
    for i in range(m.NumObj):
        m.Params.ObjNumber = i
        print(f"Obj {i} ({m.getAttr('ObjNName')}): {m.ObjNVal:.4f}")

    # 查询解中的变量值（对所有目标都一样）
    for v in m.getVars():
        print(f"{v.VarName} = {v.X}")
```

13.0 新属性（每次优化 pass 的信息）：
```python
print(f"共进行 {m.NumObjPasses} 次优化")
for p in range(m.NumObjPasses):
    m.Params.ObjNumber = p    # 或 ObjPassNumber
    print(f"pass {p}: status={m.ObjPassNStatus} obj={m.ObjPassNObjVal}")
```

## MIP vs LP 多目标

- **MIP 多目标**：每个目标作为独立 MIP 求解；上层目标固定后作为约束加入。
- **LP 多目标**：基于 warm-start 的分层单纯形，通常很快。

## 与解池结合

多目标 + 解池可以探索 Pareto 前沿附近的多个解：

```python
m.Params.PoolSearchMode = 2
m.Params.PoolSolutions = 20
# 正常 setObjectiveN 和 optimize
```

## 每个目标独立设置参数（13.0）

通过 `MultiObjSettings`：

```python
m.Params.MultiObjSettings = "obj0.prm,obj1.prm,obj2.prm"
m.optimize()
# 或在 API 中构造多目标环境
```

## 常见模式

### 词典序 (Lexicographic)

优先级严格递减：
```python
for i, expr in enumerate(objectives):
    m.setObjectiveN(expr, index=i, priority=len(objectives)-i)
```

### 加权和 (Weighted Sum)

```python
total = w1*obj1 + w2*obj2 + w3*obj3
m.setObjective(total, GRB.MINIMIZE)
# 或用 NumObj=1 等价
```

### Epsilon-Constraint

把其他目标作为约束：
```python
m.addConstr(obj2 <= eps2)
m.addConstr(obj3 <= eps3)
m.setObjective(obj1, GRB.MINIMIZE)
# 改变 eps 生成 Pareto 解
```

## 注意事项

- 多目标与**非线性目标不兼容**——全部目标必须线性
- 多目标与**解池不完全兼容**：解池存储每个 pass 的解
- `ModelSense` 对所有目标生效（都 min 或都 max）；若要混合，用负号或 weight
- 分层优化的性能主要取决于首个目标；次要目标通常很快
