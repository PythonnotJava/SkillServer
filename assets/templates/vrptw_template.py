"""
VRPTW (Vehicle Routing Problem with Time Windows) 模板。

支持：
- 硬时间窗 (hard)：只能在 [a_i, b_i] 内开始服务
- 软时间窗 (soft)：提前/延迟均惩罚
"""
import gurobipy as gp
from gurobipy import GRB
import math


def solve_vrptw(coords, demand, tw_lb, tw_ub, service_time,
                capacity, depot_id=0, mode="hard",
                early_penalty=10.0, late_penalty=10.0,
                time_limit=300):
    """
    coords:       {node: (x, y)}
    demand:       {node: int}
    tw_lb, tw_ub: {node: float}，时间窗
    service_time: {node: float}，服务时长 l_i
    capacity:     车辆容量
    mode:         "hard" 或 "soft"
    """
    V = list(coords.keys())
    C = [v for v in V if v != depot_id]

    # 行驶时间 = 欧氏距离（可替换为实际矩阵）
    T_ij = {}
    dist = {}
    for i in V:
        for j in V:
            if i != j:
                d = math.hypot(coords[i][0] - coords[j][0],
                               coords[i][1] - coords[j][1])
                dist[i, j] = d
                T_ij[i, j] = d          # 按速度 = 1 计算
    A = list(dist.keys())

    with gp.Env() as env, gp.Model(env=env, name=f"vrptw_{mode}") as m:
        m.Params.TimeLimit = time_limit

        # 决策变量
        x = m.addVars(A, vtype=GRB.BINARY, name="x")
        t = m.addVars(V, lb=0, name="t")      # 开始服务时间
        u = m.addVars(V, lb=0, ub=capacity, name="u")  # 累计容量

        if mode == "soft":
            early = m.addVars(C, lb=0, name="early")   # max(0, a_i - t_i)
            late  = m.addVars(C, lb=0, name="late")    # max(0, t_i - b_i)

        # 目标
        obj_dist = gp.quicksum(dist[i, j] * x[i, j] for (i, j) in A)
        if mode == "soft":
            obj_tw = (early_penalty * gp.quicksum(early[i] for i in C) +
                      late_penalty  * gp.quicksum(late[i]  for i in C))
            m.setObjective(obj_dist + obj_tw, GRB.MINIMIZE)
        else:
            m.setObjective(obj_dist, GRB.MINIMIZE)

        # 每客户访问一次
        for i in C:
            m.addConstr(gp.quicksum(x[i, j] for j in V if j != i) == 1)
            m.addConstr(gp.quicksum(x[j, i] for j in V if j != i) == 1)

        # 容量 (MTZ)
        for (i, j) in A:
            if i in C and j in C:
                m.addConstr(u[i] + demand[j] - u[j] <= capacity * (1 - x[i, j]))
        m.addConstr(u[depot_id] == 0)
        for i in C:
            m.addConstr(u[i] >= demand[i])

        # 时间传播
        M = max(tw_ub.values()) + max(service_time.values()) + max(T_ij.values()) + 1
        for (i, j) in A:
            if j != depot_id:  # 可以选择怎么处理回场
                m.addConstr(
                    t[i] + service_time.get(i, 0) + T_ij[i, j] - t[j] <=
                    M * (1 - x[i, j]),
                    name=f"time_{i}_{j}"
                )

        # 时间窗
        if mode == "hard":
            for i in V:
                m.addConstr(t[i] >= tw_lb.get(i, 0))
                m.addConstr(t[i] <= tw_ub.get(i, 10**9))
        else:  # soft
            for i in C:
                m.addConstr(early[i] >= tw_lb[i] - t[i])
                m.addConstr(late[i]  >= t[i] - tw_ub[i])
                # 硬界限（可选，通常设一个很宽的范围）
                m.addConstr(t[i] >= tw_lb[i] - 100)
                m.addConstr(t[i] <= tw_ub[i] + 100)
            m.addConstr(t[depot_id] == 0)

        m.optimize()

        if m.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) and m.SolCount > 0:
            print(f"\n总成本: {m.ObjVal:.2f}")
            print("路径（节点: 开始服务时间）：")
            used = [(i, j) for (i, j) in A if x[i, j].X > 0.5]
            # 从 depot 开始恢复
            starts = [j for (i, j) in used if i == depot_id]
            for start in starts:
                cur = start; route = [(depot_id, 0)]
                while cur != depot_id:
                    route.append((cur, t[cur].X))
                    nxt = [j for (i, j) in used if i == cur]
                    if not nxt:
                        break
                    cur = nxt[0]
                route.append((depot_id, t[depot_id].X if t[depot_id].X > 0 else None))
                print("  " + " -> ".join(
                    f"{n}({tt:.1f})" if tt is not None else f"{n}"
                    for n, tt in route
                ))

            if mode == "soft":
                total_early = sum(early[i].X for i in C)
                total_late  = sum(late[i].X  for i in C)
                print(f"总提前: {total_early:.1f}, 总延迟: {total_late:.1f}")
            return m.ObjVal, used


if __name__ == "__main__":
    coords = {
        0: (50, 50),   # depot
        1: (10, 20), 2: (90, 30), 3: (40, 80),
        4: (80, 90), 5: (20, 60),
    }
    demand = {0: 0, 1: 10, 2: 20, 3: 15, 4: 12, 5: 18}
    tw_lb = {0: 0, 1: 10, 2: 30, 3: 50, 4: 70, 5: 40}
    tw_ub = {0: 200, 1: 30, 2: 60, 3: 90, 4: 110, 5: 80}
    service = {0: 0, 1: 5, 2: 8, 3: 6, 4: 5, 5: 7}

    print("=== 硬时间窗 ===")
    solve_vrptw(coords, demand, tw_lb, tw_ub, service, capacity=40, mode="hard")

    print("\n=== 软时间窗 ===")
    solve_vrptw(coords, demand, tw_lb, tw_ub, service, capacity=40, mode="soft",
                early_penalty=5, late_penalty=15)
