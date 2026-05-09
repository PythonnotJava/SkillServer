"""
TSP（旅行商问题）完整实现，使用 lazy 约束消除子环。
"""
import itertools
import math
import gurobipy as gp
from gurobipy import GRB


def solve_tsp(points):
    """
    points: [(x, y), ...] 城市坐标
    返回: (总距离, 访问顺序列表)
    """
    n = len(points)

    # 欧氏距离
    def dist(i, j):
        return math.hypot(points[i][0] - points[j][0],
                          points[i][1] - points[j][1])

    m = gp.Model("tsp")

    # 无向 TSP：x[i,j] 对 i<j 定义是否使用边 (i,j)
    x = {}
    for i in range(n):
        for j in range(i + 1, n):
            x[i, j] = m.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}", obj=dist(i, j))

    m.ModelSense = GRB.MINIMIZE

    # 度约束：每个节点恰好两条关联边
    for i in range(n):
        m.addConstr(
            gp.quicksum(x[min(i, j), max(i, j)] for j in range(n) if i != j) == 2,
            name=f"deg_{i}"
        )

    def shortest_subtour(edges, n):
        """找到当前整数解中的最短环"""
        unvisited = set(range(n))
        shortest = None
        while unvisited:
            current = next(iter(unvisited))
            cycle = [current]
            unvisited.remove(current)
            while True:
                next_node = None
                for (i, j) in edges:
                    if i == current and j in unvisited:
                        next_node = j; break
                    if j == current and i in unvisited:
                        next_node = i; break
                if next_node is None:
                    break
                cycle.append(next_node)
                unvisited.remove(next_node)
                current = next_node
            if shortest is None or len(cycle) < len(shortest):
                shortest = cycle
        return shortest

    def subtour_elim(model, where):
        if where == GRB.Callback.MIPSOL:
            vals = model.cbGetSolution(model._x)
            edges = [(i, j) for (i, j), v in vals.items() if v > 0.5]
            tour = shortest_subtour(edges, n)
            if len(tour) < n:
                # 该子环中所有内部边之和 <= |tour|-1
                model.cbLazy(
                    gp.quicksum(
                        model._x[min(i, j), max(i, j)]
                        for i, j in itertools.combinations(tour, 2)
                    ) <= len(tour) - 1
                )

    m._x = x
    m.Params.LazyConstraints = 1
    m.optimize(subtour_elim)

    # 恢复路径
    edges = [(i, j) for (i, j), var in x.items() if var.X > 0.5]
    tour = shortest_subtour(edges, n)
    return m.ObjVal, tour


if __name__ == "__main__":
    import random
    random.seed(42)
    pts = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(15)]
    obj, tour = solve_tsp(pts)
    print(f"最短距离: {obj:.2f}")
    print(f"路径: {tour}")
