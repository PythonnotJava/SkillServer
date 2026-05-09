"""
状态-动作时序 MIP 模板。
适用于：数字华容道、密集仓库取货、方块推箱子、智能体路径规划等。

核心建模思想：
- 时间步 k = 0..K
- 状态变量 x[k,*]: 第 k 步完成后的状态
- 动作变量 y[k,*]: 第 k 步执行的动作
- 状态更新：x[k,*] = f(x[k-1,*], y[k,*])
"""
import gurobipy as gp
from gurobipy import GRB


def solve_puzzle(init_state, target_state, neighbors, K_max):
    """
    数字华容道求解器（示例）。

    init_state:   {item_id: position}，初始各数字的位置
    target_state: {item_id: position}，目标位置
    neighbors:    {position: [相邻位置列表]}
    K_max:        最大移动步数（K_max 越大越容易有解但规模越大）
    """
    items = list(init_state.keys())
    positions = list(neighbors.keys())

    # 邻接矩阵 A[p,q] ∈ {0,1}: 能否一步从 p 到 q
    A = {}
    for p in positions:
        for q in positions:
            A[p, q] = 1 if q in neighbors[p] else 0

    m = gp.Model("puzzle")
    m.Params.TimeLimit = 300

    # 状态：x[k,i,p] = 1 ⇔ 第 k 步后数字 i 在位置 p
    x = m.addVars(range(K_max + 1), items, positions,
                  vtype=GRB.BINARY, name="x")

    # 动作：y[k,i,p,q] = 1 ⇔ 第 k 步把数字 i 从 p 移到 q
    y = m.addVars(range(K_max + 1), items, positions, positions,
                  vtype=GRB.BINARY, name="y")

    # --- 目标：最小化总动作数 ---
    m.setObjective(
        gp.quicksum(y[k, i, p, q]
                    for k in range(K_max + 1)
                    for i in items
                    for p in positions
                    for q in positions),
        GRB.MINIMIZE
    )

    # --- 初始状态 ---
    for i in items:
        for p in positions:
            if init_state[i] == p:
                m.addConstr(x[0, i, p] == 1)
            else:
                m.addConstr(x[0, i, p] == 0)

    # --- 第 0 步无动作 ---
    m.addConstr(
        gp.quicksum(y[0, i, p, q] for i in items for p in positions for q in positions) == 0
    )

    # --- 每数字在每步恰好一个位置 ---
    for k in range(K_max + 1):
        for i in items:
            m.addConstr(gp.quicksum(x[k, i, p] for p in positions) == 1)

    # --- 每位置至多一个数字 ---
    for k in range(K_max + 1):
        for p in positions:
            m.addConstr(gp.quicksum(x[k, i, p] for i in items) <= 1)

    # --- 合法动作 ---
    for k in range(1, K_max + 1):
        for i in items:
            for p in positions:
                for q in positions:
                    # 必须相邻
                    m.addConstr(y[k, i, p, q] <= A[p, q])
                    # 目的地 q 在 k-1 步必须为空
                    m.addConstr(
                        y[k, i, p, q] <= 1 - gp.quicksum(x[k-1, j, q] for j in items)
                    )

    # --- 每步至多一个动作 ---
    for k in range(K_max + 1):
        m.addConstr(
            gp.quicksum(y[k, i, p, q] for i in items for p in positions for q in positions) <= 1
        )

    # --- 状态更新（最关键！）---
    # x[k-1,i,p] - sum_q y[k,i,p,q] + sum_q y[k,i,q,p] = x[k,i,p]
    for k in range(1, K_max + 1):
        for i in items:
            for p in positions:
                m.addConstr(
                    x[k-1, i, p]
                    - gp.quicksum(y[k, i, p, q] for q in positions)
                    + gp.quicksum(y[k, i, q, p] for q in positions)
                    == x[k, i, p],
                    name=f"update_{k}_{i}_{p}"
                )

    # --- 终态 ---
    for i in items:
        m.addConstr(x[K_max, i, target_state[i]] == 1)

    # --- 模型收紧：动作前置（减少空转步骤）---
    for k in range(K_max):
        m.addConstr(
            gp.quicksum(y[k, i, p, q] for i in items for p in positions for q in positions) >=
            gp.quicksum(y[k+1, i, p, q] for i in items for p in positions for q in positions)
        )

    m.optimize()

    if m.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) and m.SolCount > 0:
        total_moves = int(m.ObjVal + 0.5)
        print(f"最少步数: {total_moves}")
        print("动作序列:")
        for k in range(1, K_max + 1):
            for i in items:
                for p in positions:
                    for q in positions:
                        if y[k, i, p, q].X > 0.5:
                            print(f"  第 {k} 步: 数字 {i} 从位置 {p} → {q}")
        return total_moves
    return None


if __name__ == "__main__":
    # 3x3 数字华容道示例
    # 位置编号 0-8，目标：数字 i 在位置 i，位置 8 空
    # 初始：{0:0, 1:1, 2:2, 3:6, 4:5, 5:3, 6:7, 7:4}（即 0 2 5; 7 6 4; 8 3 ?）
    # 邻接（网格上下左右）
    def build_grid_neighbors(rows=3, cols=3):
        neigh = {}
        for i in range(rows):
            for j in range(cols):
                p = i * cols + j
                neigh[p] = []
                if i > 0: neigh[p].append((i-1)*cols + j)
                if i < rows-1: neigh[p].append((i+1)*cols + j)
                if j > 0: neigh[p].append(i*cols + j - 1)
                if j < cols-1: neigh[p].append(i*cols + j + 1)
        return neigh

    neighbors = build_grid_neighbors(3, 3)

    init_state = {0: 0, 1: 1, 2: 2, 3: 5, 4: 6, 5: 3, 6: 4, 7: 7}
    target_state = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7}

    solve_puzzle(init_state, target_state, neighbors, K_max=10)
