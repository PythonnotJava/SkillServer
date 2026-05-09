# 中文经典建模案例库

本文收录了一些中文典型案例，涵盖生产计划、数论方程、机组排班、配送网络、华容道、仓储、机器人组装生产计划等。每个案例都以**完整问题描述 → 决策变量 → 约束 → 目标 → Gurobi 代码**的方式组织。

## 目录

1. [生产计划优化（带雇佣 / 外包 / 库存 / 缺货）](#案例-1生产计划优化)
2. [数论方程整数解（分式消除 / 乘法消除）](#案例-2数论方程整数解)
3. [机组排班（航班邻接网络 + 多商品流）](#案例-3机组排班)
4. [配送网络（商品流 + 车辆数上取整）](#案例-4配送网络规划)
5. [数字华容道（状态-动作时序 MIP）](#案例-5数字华容道)
6. [密集仓库取货（NIPA vs NIPF 建模）](#案例-6密集存储仓库取货)
7. [机器人组装生产计划（多层 BOM + 指示约束）](#案例-7机器人组装生产计划)

---

## 案例 1：生产计划优化

### 问题描述

某公司生产可折叠桌子（单价 300 元），6 个月需求预测：

| 月份 | 1     | 2     | 3     | 4     | 5     | 6     |
| ---- | ----- | ----- | ----- | ----- | ----- | ----- |
| 需求 | 20000 | 40000 | 42000 | 35000 | 19000 | 18500 |

参数：

- 原材料成本 90 元/件；人工 5 工时/件
- 1 月初员工 1000 人，月工时 20×8=160 小时；加班每人不超 20h/月
- 正常薪酬 30 元/h，加班 40 元/h
- 月库存成本 15 元/件；缺货成本 35 元/件
- 外包成本 200 元/件
- 雇佣/解雇成本 5000 / 8000 元/人
- 1 月初库存 15000 件；6 月末至少保有 10000 件

决策制定生产、工人、雇佣解雇计划，最大化 6 个月净收益。

### 决策变量（i = 1..6）

| 变量 | 类型           | 含义                  |
| ---- | -------------- | --------------------- |
| x_i  | 非负整数       | 当月生产量            |
| y_i  | 非负整数       | 当月外包量            |
| z_i  | 0-1            | 当月是否缺货          |
| I_i  | 非负整数       | 月末库存              |
| e_i  | 整数（无约束） | 生产+库存与需求的差值 |
| L_i  | 非负整数       | 缺货量                |
| H_i  | 非负整数       | 当月雇佣数            |
| F_i  | 非负整数       | 当月解雇数            |
| P_i  | 非负整数       | 当月员工数            |
| O_i  | 非负连续       | 当月总加班时间        |
| S_i  | 非负整数       | 当月实际销售量        |

### 目标

```
max ∑_{i=1..6} [300·S_i - 90·x_i - 200·y_i
                - 40·O_i - P_i·(30·8·20)
                - 15000   (固定管理费)
                - 15·I_i - 35·L_i
                - 5000·H_i - 8000·F_i]
```

### 约束

**边界**：`I_0 = 15000, P_0 = 1000, L_0 = 0, S_0 = 0, I_6 >= 10000`

**物料平衡**：

```
I_{i-1} + x_i + y_i + e_i = d_i    (生产+库存+外包+差值 = 需求)
I_{i-1} + x_i + y_i - S_i = I_i    (本月库存)
```

**缺货刻画（双向指示约束）** — Big-M=max_i d_i：

```
e_i - M·z_i <= 0            (z_i=0 ⇒ e_i<=0)
-(e_i-1) - M·(1-z_i) <= 0   (z_i=1 ⇒ e_i>=1)
L_i - e_i - M·(1-z_i) <= 0  (z_i=1 ⇒ L_i<=e_i)
e_i - L_i - M·(1-z_i) <= 0  (z_i=1 ⇒ L_i>=e_i)
```

**销售 / 员工动态**：

```
S_i = d_i - L_i
P_{i-1} + H_i - F_i = P_i
```

**工时**：

```
5·x_i <= 8·20·P_i + O_i     (生产工时 <= 正班 + 加班)
O_i <= 20·P_i                (每人加班最多 20h)
```

### Gurobi 代码

```python
import gurobipy as gp
from gurobipy import GRB

class Instance:
    def __init__(self):
        self.period_num = 7        # 0..6 (0 是初始态)
        self.raw_material_cost = 90
        self.unit_product_time = 5
        self.price = 300
        self.init_employee_num = 1000
        self.init_inventory = 15000
        self.normal_unit_salary = 30
        self.overtime_unit_salary = 40
        self.work_day_num = 20
        self.work_time_each_day = 8
        self.overtime_upper_limit = 20
        self.outsource_unit_cost = 200
        self.unit_inventory_cost = 15
        self.unit_shortage_cost = 35
        self.hire_cost = 5000
        self.fire_cost = 8000
        self.inventory_LB_of_last_month = 10000
        self.demand = [0, 20000, 40000, 42000, 35000, 19000, 18500]

def solve(ins):
    T = range(1, ins.period_num)
    M = max(ins.demand)

    m = gp.Model("production")

    x = m.addVars(T, vtype=GRB.INTEGER, name="x")
    y = m.addVars(T, vtype=GRB.INTEGER, name="y")
    z = m.addVars(T, vtype=GRB.BINARY, name="z")
    I = m.addVars([0]+list(T), vtype=GRB.INTEGER, name="I")
    e = m.addVars(T, lb=-GRB.INFINITY, vtype=GRB.INTEGER, name="e")
    L = m.addVars(T, vtype=GRB.INTEGER, name="L")
    H = m.addVars(T, vtype=GRB.INTEGER, name="H")
    F = m.addVars(T, vtype=GRB.INTEGER, name="F")
    P = m.addVars([0]+list(T), vtype=GRB.INTEGER, name="P")
    O = m.addVars(T, lb=0, name="O")
    S = m.addVars(T, vtype=GRB.INTEGER, name="S")

    # 边界
    m.addConstr(I[0] == ins.init_inventory)
    m.addConstr(P[0] == ins.init_employee_num)
    m.addConstr(I[6] >= ins.inventory_LB_of_last_month)

    # 物料与动态
    for i in T:
        m.addConstr(I[i-1] + x[i] + y[i] + e[i] == ins.demand[i])
        m.addConstr(I[i-1] + x[i] + y[i] - S[i] == I[i])
        m.addConstr(S[i] == ins.demand[i] - L[i])
        m.addConstr(P[i-1] + H[i] - F[i] == P[i])
        m.addConstr(ins.unit_product_time * x[i] <=
                    ins.work_time_each_day * ins.work_day_num * P[i] + O[i])
        m.addConstr(O[i] <= ins.overtime_upper_limit * P[i])

        # 缺货指示双向
        m.addConstr(e[i] - M*z[i] <= 0)
        m.addConstr(-(e[i]-1) - M*(1-z[i]) <= 0)
        m.addConstr(L[i] - e[i] - M*(1-z[i]) <= 0)
        m.addConstr(e[i] - L[i] - M*(1-z[i]) <= 0)

    # 目标
    m.setObjective(
        gp.quicksum(
            ins.price * S[i]
            - ins.raw_material_cost * x[i]
            - ins.outsource_unit_cost * y[i]
            - ins.overtime_unit_salary * O[i]
            - P[i] * ins.normal_unit_salary * ins.work_time_each_day * ins.work_day_num
            - 15000
            - ins.unit_inventory_cost * I[i]
            - ins.unit_shortage_cost * L[i]
            - ins.hire_cost * H[i]
            - ins.fire_cost * F[i]
            for i in T
        ),
        GRB.MAXIMIZE
    )
    m.optimize()

    if m.Status == GRB.OPTIMAL:
        print(f"最大净收益: {m.ObjVal:.2f}")
        for i in T:
            print(f"月 {i}: 生产={int(x[i].X)}, 外包={int(y[i].X)}, "
                  f"缺货={int(L[i].X)}, 库存={int(I[i].X)}, "
                  f"员工={int(P[i].X)}, 加班={O[i].X:.1f}h")

if __name__ == "__main__":
    solve(Instance())
```

### 要点总结

- **Big-M 取值**：`M = max_i d_i`（比 `1e8` 紧 4 个数量级），能显著加速 LP 松弛
- **双向 indicator**：z=1⇔e≥1 用 4 条约束精确刻画
- **e 是整数且无符号约束**：需要设 `lb=-GRB.INFINITY`

---

## 案例 2：数论方程整数解

### 问题

找 `a/(b+c) + b/(a+c) + c/(a+b) = 4` 的正整数解。

### 方法 1：引入辅助变量 → MIQCP

```
x_i = m_i · (x_{i2} + x_{i3})    (二次等式)
m_1 + m_2 + m_3 = 4
```

转为 MIQCP，Gurobi 求得 `a=35, b=132, c=627`。

⚠ 验证时发现**违反量约 1e-6**，原因是 Gurobi 默认 `FeasibilityTol=1e-6`，刚好在容差内。

### 方法 2：消除除号（两边同乘）

```python
# 方程两边同乘 (b+c)(a+c)(a+b) 得多项式等式
# 引入辅助变量 u_i = x_j + x_k 降阶
# 最终是 MIQCP（含三次项的降阶形式）
```

但此问题的真实正整数最小解是**三个 80 位大整数**，Gurobi 2 小时都无法找到。

### 方法 3：只要整数（不必正）

如果允许负整数：

- 需将 `x_1 + x_2 ≠ 0` 转为 `|x_1 + x_2| >= 1`
- 引入 `u_i = x_j + x_k`，`u_i^abs = |u_i|`，约束 `u_i^abs >= 1`
- Gurobi 快速找到 `a=-1, b=11, c=4`

### 关键教训

1. **分式约束**必须消除除号才能求解
2. **精度警惕**：MIQCP 中 1e-6 容差可能让非可行解"通过"
3. **整数 vs 正整数**：极小的问题描述变化可能让难度天差地别

---

## 案例 3：机组排班

### 问题

将 206 个航班分配给 21 名机组人员（正机长/副机长/乘机），使可起飞航班数最大。

### 核心建模思路：**航班邻接网络 + 多商品流**

不直接对"航班 i 分配给机组 r"建模，而是对"连续执行的两航班 (i,j)"建模。

**航班邻接网络** `G = (F, A)`：

- 节点：航班（含虚拟航班 = 基地）
- 弧 `(i,j) ∈ A` 当且仅当 `航班 i 终点 = 航班 j 起点` 且 `T_i^到 + τ <= T_j^出`

### 决策变量

| 变量          | 含义                                                     |
| ------------- | -------------------------------------------------------- |
| `x^r_{i,j}` | 0-1，机组 r 连续执行 i→j                                |
| `z^{r,k}_i` | 0-1，机组 r 以角色 k 执行 i                              |
| `w_i`       | 0-1，航班 i 是否满足起飞资格（至少 1 正机长 + 1 副机长） |

### 目标

```
max ∑ w_i     (最大化可起飞航班数)
```

### 约束

```
∀r: ∑_{j ∈ F, i ∈ F_out(b_r)} x^r_{i,j} <= 1     (每人最多从本基地出发一次)

∀r: ∑_{j ∈ F_in(b_r)} ∑_i x^r_{j,i} = ∑_{i ∈ F_out(b_r)} ∑_j x^r_{i,j}
       (出发一次必须返回)

∀r, i ∉ F_virtual:                                 (流平衡)
∑_j x^r_{i,j} = ∑_j x^r_{j,i}

∀i, r:  ∑_j x^r_{i,j} = ∑_k z^{r,k}_i              (分配则必任一角色)
∀i, r, k: z^{r,k}_i <= Q_{r,k}                     (资质约束)

∀i: w_i <= ∑_r z^{r,1}_i                            (满足需要 >=1 正机长)
∀i: w_i <= ∑_r z^{r,2}_i                            (满足需要 >=1 副机长)
```

### 规模爆炸控制

原完全图 |A| = 85284；经邻接网络预处理后 |A| = 6448，规模降 93%。

对更大数据集（13956 航班、465 人），仍会产生 ~84 亿决策变量。应用**骨干网络生成 (Backbone Network Generation)** 算法：设置 `E_max`，从邻接网络中按"出发时间差接近 D_max 的弧"随机删除，保留最关键弧。

### 求解结果

206+1 航班、21 机组、6448 弧、21988 约束、148656 整数变量，Gurobi 最优值 207（全部航班可起飞），20s 内求解。

---

## 案例 4：配送网络规划

### 问题

湖北 5 + 广东 5 = 10 个分拨中心之间的快递运输。车辆容量 4000 件/辆。成本 = 5×距离 + 300 元/车。要求每个商品流（起点-终点对）**路径唯一**。

### 决策变量

| 变量          | 类型     | 含义                         |
| ------------- | -------- | ---------------------------- |
| `x^p_{i,j}` | 0-1      | 弧 (i,j) 是否运输商品流 p    |
| `f^p_{i,j}` | 非负整数 | 弧 (i,j) 运输商品流 p 的件数 |
| `y_{i,j}`   | 非负整数 | 省际弧需车辆数               |

### 目标

```
min  ∑_{(i,j)∈S} ∑_p c_{ij}·(f^p_{ij}/Q)    +    ∑_{(i,j)∈D} c_{ij}·y_{ij}
     ─────── 省内转运（按件数成本） ───────    ── 省际（按车辆数成本） ──
```

其中 `c_{ij} = 5·d_{ij} + 300`。

### 关键约束

**流平衡**（每个商品流、每个节点）：

```
∑_{(i,j)} x^p_{ij} - ∑_{(j,i)} x^p_{ji} = b^p_i
# b^p_{起点}=1, b^p_{终点}=-1, 其他=0
```

**车辆数上取整**：`y_{ij} = ⌈∑_p f^p_{ij} / Q⌉`

线性化为**两条不等式**（配合 min 目标可省略其中一条）：

```
y_{ij} >= (∑_p f^p_{ij}) / Q
y_{ij} - 1 <= (∑_p f^p_{ij}) / Q       ← 目标最小化 y 时此约束多余
```

**路径-流量耦合**：

```
f^p_{ij} = q_p · x^p_{ij}        (若走此弧则载量 = 需求 q_p；否则 0)
```

展开：`f^p_{ij} - q_p·x^p_{ij} = 0`

### 规模与复杂度

决策变量复杂度：O(|K|·|A|)，约束复杂度同。NP-hard，大规模需定制启发式。

### 扩展：限制转运次数

对单个商品流转运次数上限 U：

```
∑_{(i,j)∈A} x^p_{ij} <= U,    ∀p ∈ K
```

---

## 案例 5：数字华容道

### 问题

n×n 网格中有 n²-1 个数字滑块，通过与空格相邻交换移动，求**最少步数**还原数字按 1..n²-1 排列。

### 决策变量

**状态变量**（在第 k 步完成后）：

```
x_{k,i,p} ∈ {0,1}:  数字 i 是否在位置 p     (∀k=0..K, ∀i ∈ I, ∀p ∈ P)
```

**动作变量**：

```
y_{k,i,p,q} ∈ {0,1}: 第 k 步把数字 i 从 p 移到 q
```

K 是移动步数上限（需预设，过大会爆炸，过小可能无解）。

### 目标

```
min  ∑_{k,i,p,q} y_{k,i,p,q}        (总移动次数)
```

### 核心约束

**位置-数字唯一性**：

```
∀k, ∀i: ∑_p x_{k,i,p} = 1           (每数字恰占一位)
∀k, ∀p: ∑_i x_{k,i,p} <= 1           (每位置至多一数字；可空)
```

**合法移动**（只能移到邻居，且目的地必须是空位）：

```
y_{k,i,p,q} <= A_{p,q}                               (邻接条件)
y_{k,i,p,q} <= 1 - ∑_i x_{k-1,i,q}                   (目的地空)
```

**状态更新**（最关键）：

```
x_{k-1,i,p} - ∑_q y_{k,i,p,q} + ∑_q y_{k,i,q,p} = x_{k,i,p}
#   上一步在 p         移出 p            移入 p         本步在 p
```

**每步至多一次移动**：

```
∀k: ∑_{i,p,q} y_{k,i,p,q} <= 1
```

**终点约束**：

```
x_{K,i,i} = 1,     ∀i ∈ I       (按编号归位)
```

### 模型收紧（减小规模）

若 K 取值偏大，中间可能有"空转"步骤。加入单调性约束：

```
∑_{i,p,q} y_{k,i,p,q} >= ∑_{i,p,q} y_{k+1,i,p,q}     (移动集中在前面)
```

### 结果分析

3×3 算例通常 <10s；4×4 算例难度陡增，部分 30 分钟无解。

决策变量复杂度：O(K·|I|·|P|²)。

---

## 案例 6：密集存储仓库取货（NIPA vs NIPF）

### 问题

密集存储仓库（无巷道），目标货物要移到对应 IO 口。目标：最小化总移动步数。

### 建模思路一：NIPA (Normal Item Position-Aware)

每个非目标货物也有编号，决策变量：`x_{k,i,p}, y_{k,i,p,q}`，和数字华容道一样，规模巨大。

### 建模思路二：NIPF (Normal Item Position-Free) — 推荐

**关键观察**：非目标货物的具体编号**不重要**。只需区分：位置是否被占、目标货物在哪。

#### 决策变量（NIPF）

```
x^k_p ∈ {0,1}:     第 k 步后位置 p 是否被占用（不区分是哪个货物）
y^k_{p,r} ∈ {0,1}: 第 k 步后目标货物 r 是否在位置 p
z^k_{p,q} ∈ {0,1}: 第 k 步中，位置 p 的货物移到位置 q（不区分货物类型）
w^k_{p,q,r} ∈ {0,1}: 第 k 步中，目标货物 r 从 p 移到 q
```

#### 核心约束

**占用守恒**：

```
∑_p x^k_p = |P| - e     (e = 空格数，恒定)
```

**位置更新**：

```
x^{k-1}_p - ∑_q z^k_{p,q} + ∑_q z^k_{q,p} = x^k_p
```

**目标货物位置更新**：

```
y^{k-1}_{p,r} - ∑_q w^k_{p,q,r} + ∑_q w^k_{q,p,r} = y^k_{p,r}
```

**合法性**：

```
∑^K_{k=1} z^k_{p,q} <= A_{p,q} · K         (邻接限制)
z^k_{p,q} <= 1 - x^{k-1}_q                  (目的地空)
∑_{p,q} z^k_{p,q} <= 1                      (每步一动)
```

**每目标货物唯一占位**：

```
∀k, ∀r: ∑_p y^k_{p,r} = 1
∀k, ∀p: ∑_r y^k_{p,r} <= 1
```

**IO 约束**：

```
y^K_{IO_r, r} = 1,     ∀r ∈ D
```

**目标移动耦合**（`w^k_{p,q,r} = y^{k-1}_{p,r} · z^k_{p,q}`）线性化：

```
w^k_{p,q,r} >= y^{k-1}_{p,r} + z^k_{p,q} - 1
w^k_{p,q,r} <= y^{k-1}_{p,r}
w^k_{p,q,r} <= z^k_{p,q}
```

#### 性能对比

R422 算例集：

- NIPA 平均求解时间：~278s（许多算例 7200s 内无解）
- NIPF 平均求解时间：~25s（11× 加速）
- 最大单算例加速：1015×

### 扩展：允许同时移动

引入 `f_k ∈ {0,1}`（第 k 步是否有货物移动），目标改为 `min ∑_k f_k`（最小化步数而非移动总数），添加 `f_k >= z^k_{p,q} ∀p,q`。

---

## 案例 7：机器人组装生产计划

### 问题（"华数杯" 2022 B 题）

WPCR 由 3 大组件（A/B/C）组成，每大组件由若干小组件组成（A1..A3, B1..B2, C1..C3）。每天有需求量、工时上限、生产准备费用、库存成本等。计划一周生产。

### 决策变量

- **生产数量**：`w_i`（WPCR），`x_{i,j}`（大组件 j），`z_{i,k}`（小组件 k）
- **期初库存**：`yw_i`（WPCR），`y_{i,j}`，`yz_{i,k}`（下标 `i ∈ 1..N+1`）
- **是否生产指示**：`lw_i`, `l_{i,j}`, `lz_{i,k}`（0-1）

### 目标

```
min  Z = Z_1 + Z_2
Z_1 = ∑_i (∑_j S_j·l_{i,j} + ∑_k Sz_k·lz_{i,k} + S_w·lw_i)    # 生产准备费
Z_2 = ∑_i (∑_j p_j·y_{i,j} + ∑_k p_k·yz_{i,k} + p_w·yw_i)    # 库存费
```

### 关键约束

**初终库存为 0**：

```
y_{1,j} = 0, yw_1 = 0, yz_{1,k} = 0
y_{N+1,j} = 0, yw_{N+1} = 0, yz_{N+1,k} = 0
```

**工时**：`∑_j t_j · x_{i,j} <= T_i`

**库存动态（WPCR）**：`w_i + yw_i - Nw_i = yw_{i+1}`

**库存动态（大组件）**：`y_{i,j} + x_{i,j} - k_j·w_i = y_{i+1,j}`

**库存动态（小组件）**：`yz_{i,k} + z_{i,k} - ∑_j h_{j,k}·x_{i,j} = yz_{i+1,k}`

**需求满足**：`yw_i + w_i >= Nw_i`

**组装资料数量关系**：

- WPCR 需要大组件：`k_j·w_i <= x_{i,j} + y_{i,j}`
- 大组件需要小组件：`h_{j,k}·x_{i,j} <= z_{i,k} + yz_{i,k}`

**是否生产指示**（利用**逆否命题**建模）：

要表达 `w_i > 0 ⇒ lw_i = 1`（等价 `w_i >= 1`，因为 w 整数）：

```
1 - w_i - M·(1 - lw_i) <= 0    # M 取 1-w 的上界，此处 M=1 即可
 ⇔ w_i >= lw_i
```

要表达 `lw_i = 0 ⇒ w_i = 0`：

```
w_i <= M·lw_i,   M = ∑_i Nw_i
```

完整指示约束对（每种产品都加一对）：

```
w_i >= lw_i
w_i <= M·lw_i
```

### 问题二变体（组件需提前 1 天生产）

问题二要求大组件要提前 1 天入库才能用于 WPCR 组装，小组件要提前 1 天入库才能用于大组件。

- 删除约束 `y_{1,j} = 0, yz_{1,k} = 0`（允许初始库存）
- 修改 `k_j·w_i <= x_{i,j} + y_{i,j}` 为 `k_j·w_i <= y_{i,j}` （只能用昨日库存）
- 修改 `h_{j,k}·x_{i,j} <= z_{i,k} + yz_{i,k}` 为 `h_{j,k}·x_{i,j} <= yz_{i,k}`
- 添加循环约束：`yw_1 = yw_{N+1}, y_{1,j} = y_{N+1,j}, yz_{1,k} = yz_{N+1,k}`（周生产循环）

### 结果

问题一（无提前）最优成本 6260.9 元；问题二（提前）最优成本 179455.5 元。**假设微调导致目标值增长 18 倍**，说明建模假设的重要性。

### 用 `addGenConstrIndicator` 的更简洁写法

```python
# 若 lw[i] = 1，则 w[i] >= 1
m.addGenConstrIndicator(lw[i], True, w[i] >= 1)
# 若 lw[i] = 0，则 w[i] <= 0
m.addGenConstrIndicator(lw[i], False, w[i] <= 0)
```

比手写 Big-M 更易读，数值上也更稳定（Gurobi 内部会自动选择最佳 Big-M 或用原生 indicator）。

---

## 通用教训

1. **决策变量设计决定模型规模**：从可行解倒推决策变量往往比盲目建模更紧凑（如机组排班用"弧"而非"航班"）
2. **消除对称性**：同质车辆、同质机组要加破对称约束
3. **逆否命题**：双向指示约束最多 2 条不等式而非 4 条
4. **Big-M 紧化**：`M` 取"该约束能容忍的最紧上界"而非常数 `1e8`
5. **模型降维**：非目标信息可忽略的场景（如仓库非目标货物编号）能带来 100× 以上加速
6. **求解精度验证**：复杂模型转换后要代回原式验证违反量
