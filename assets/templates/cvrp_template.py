"""
CVRP (带容量约束的车辆路径规划) 模板。

默认使用 CVRP2（双下标 + MTZ），对同质车辆最紧凑。
若需异质车辆或分车分析，改用 CVRP1-1 + lazy DFJ 版本。
"""
import gurobipy as gp
from gurobipy import GRB
import math


def solve_cvrp_mtz(coords, demand, capacity, depot_id=0):
    """
    CVRP2 实现（双下标 + MTZ 约束）。

    coords: {node_id: (x, y)}，含 depot
    demand: {node_id: int}，depot 的 demand 通常为 0
    capacity: 单车容量
    depot_id: 车场节点编号
    """
    V = list(coords.keys())
    C = [v for v in V if v != depot_id]

    # 欧氏距离
    dist = {}
    for i in V:
        for j in V:
            if i != j:
                dist[i, j] = math.hypot(coords[i][0] - coords[j][0],
                                         coords[i][1] - coords[j][1])

    A = list(dist.keys())

    with gp.Env() as env, gp.Model(env=env, name="cvrp_mtz") as m:
        m.Params.TimeLimit = 300

        x = m.addVars(A, vtype=GRB.BINARY, name="x")
        u = m.addVars(V, lb=0, ub=capacity, name="u")

        m.setObjective(
            gp.quicksum(dist[i, j] * x[i, j] for (i, j) in A),
            GRB.MINIMIZE
        )

        # 每客户恰一车访问
        for i in C:
            m.addConstr(gp.quicksum(x[i, j] for j in V if j != i) == 1,
                        name=f"out_{i}")
            m.addConstr(gp.quicksum(x[j, i] for j in V if j != i) == 1,
                        name=f"in_{i}")

        # MTZ + 容量
        for (i, j) in A:
            if i in C and j in C:
                m.addConstr(
                    u[i] + demand[j] - u[j] <= capacity * (1 - x[i, j]),
                    name=f"mtz_{i}_{j}"
                )

        # 车场起点 u=0
        m.addConstr(u[depot_id] == 0)
        # 客户处累计需求 >= 自身需求
        for i in C:
            m.addConstr(u[i] >= demand[i])

        m.optimize()

        if m.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) and m.SolCount > 0:
            print(f"\n总成本: {m.ObjVal:.2f}")
            used = [(i, j) for (i, j) in A if x[i, j].X > 0.5]
            _print_routes(used, depot_id)
            return m.ObjVal, used
        else:
            print(f"无解 status={m.Status}")
            return None, None


def _print_routes(edges, depot):
    """从弧集合恢复路径并打印"""
    out = {i: j for (i, j) in edges if i == depot}
    # 从 depot 出发的每条边开始追踪
    starts = [j for (i, j) in edges if i == depot]
    for start in starts:
        route = [depot, start]
        cur = start
        while cur != depot:
            nxt_list = [j for (i, j) in edges if i == cur]
            if not nxt_list:
                break
            cur = nxt_list[0]
            route.append(cur)
        print(f"  路径: {' -> '.join(map(str, route))}")


# ============ CVRP1-1 + Lazy DFJ（支持异质车辆） ============

def solve_cvrp_dfj(coords, demand, capacity, K, depot_id=0):
    """
    CVRP1-1 + Lazy DFJ 回调。
    K: 车辆数
    """
    V = list(coords.keys())
    C = [v for v in V if v != depot_id]

    dist = {}
    for i in V:
        for j in V:
            if i != j:
                dist[i, j] = math.hypot(coords[i][0] - coords[j][0],
                                         coords[i][1] - coords[j][1])
    A = list(dist.keys())

    m = gp.Model("cvrp_dfj")
    x = m.addVars(range(K), A, vtype=GRB.BINARY, name="x")

    m.setObjective(
        gp.quicksum(dist[i, j] * x[k, i, j]
                    for k in range(K) for (i, j) in A),
        GRB.MINIMIZE
    )

    # 每客户恰一车访问
    for i in C:
        m.addConstr(
            gp.quicksum(x[k, i, j] for k in range(K)
                        for j in V if j != i) == 1
        )
    # 每车容量
    for k in range(K):
        m.addConstr(
            gp.quicksum(demand[i] * x[k, i, j]
                        for i in C for j in V if j != i) <= capacity
        )
    # 流平衡
    for k in range(K):
        for i in C:
            m.addConstr(
                gp.quicksum(x[k, i, j] for j in V if j != i) ==
                gp.quicksum(x[k, j, i] for j in V if j != i)
            )
        # 发车 <= 1
        m.addConstr(gp.quicksum(x[k, depot_id, j] for j in C) <= 1)

    def subtours(k, sol):
        edges = [(i, j) for (i, j) in A if sol[k, i, j] > 0.5]
        visited = set()
        result = []
        for start in C:
            if start in visited:
                continue
            cycle = []
            cur = start
            while cur not in visited and cur != depot_id:
                visited.add(cur)
                cycle.append(cur)
                nxt = [j for (i, j) in edges if i == cur]
                if not nxt:
                    break
                cur = nxt[0]
            if len(cycle) >= 2 and depot_id not in cycle:
                result.append(cycle)
        return result

    def cb(model, where):
        if where == GRB.Callback.MIPSOL:
            sol = model.cbGetSolution(model._x)
            for k in range(K):
                for S in subtours(k, sol):
                    model.cbLazy(
                        gp.quicksum(model._x[k, i, j]
                                    for i in S for j in S if i != j) <= len(S) - 1
                    )

    m._x = x
    m.Params.LazyConstraints = 1
    m.Params.TimeLimit = 300
    m.optimize(cb)
    return m


if __name__ == "__main__":
    # 小算例
    coords = {
        0: (50, 50),    # depot
        1: (10, 20), 2: (90, 30), 3: (40, 80),
        4: (80, 90), 5: (20, 60), 6: (60, 10),
    }
    demand = {0: 0, 1: 15, 2: 20, 3: 10, 4: 25, 5: 18, 6: 12}
    capacity = 50
    solve_cvrp_mtz(coords, demand, capacity)
