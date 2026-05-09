"""
非线性建模模板（Gurobi 13.0 推荐方式 = Nonlinear Constraints）。
示例：非线性回归 + 带三角函数的约束。
"""
import gurobipy as gp
from gurobipy import GRB, nlfunc


def nonlinear_regression():
    """
    拟合 y = a * exp(b*x) + c 到数据点，最小化平方误差。
    """
    xs = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    ys = [1.05, 1.7, 2.75, 4.6, 7.4, 12.2, 20.1]
    n = len(xs)

    m = gp.Model("regression")

    a = m.addVar(lb=0.1, ub=5.0, name="a")
    b = m.addVar(lb=-2.0, ub=2.0, name="b")
    c = m.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name="c")

    # 残差 r_i = pred_i - y_i
    r = m.addVars(n, lb=-GRB.INFINITY, name="r")

    # 非线性预测：pred_i = a * exp(b * x_i) + c
    for i, xi in enumerate(xs):
        m.addConstr(r[i] == a * nlfunc.exp(b * xi) + c - ys[i])

    # 最小化平方和（二次目标）
    m.setObjective(gp.quicksum(r[i] * r[i] for i in range(n)), GRB.MINIMIZE)

    # 局部最优即可（快）
    m.Params.OptimalityTarget = 1
    m.Params.NonConvex = 2   # 二次 * 非线性 -> 非凸
    m.optimize()

    if m.Status in (GRB.OPTIMAL, GRB.LOCALLY_OPTIMAL):
        print(f"a = {a.X:.4f}")
        print(f"b = {b.X:.4f}")
        print(f"c = {c.X:.4f}")
        print(f"SSE = {m.ObjVal:.6f}")


def nonlinear_constraint_example():
    """
    演示含 sin/cos/sqrt/exp/tanh/signpow 的非线性约束。
        max  x + y
        s.t. sin(x) + cos(y) <= 0.5
             sqrt(x + 1) + exp(-y) >= 1.5
             tanh(x - y) == 0.3   (13.0 新)
             signpow(x, 2) <= 4   (13.0 新, 等价 x*|x| <= 4)
    """
    m = gp.Model("nl_demo")
    x = m.addVar(lb=0, ub=5, name="x")
    y = m.addVar(lb=-3, ub=3, name="y")

    m.addConstr(nlfunc.sin(x) + nlfunc.cos(y) <= 0.5)
    m.addConstr(nlfunc.sqrt(x + 1) + nlfunc.exp(-y) >= 1.5)
    m.addConstr(nlfunc.tanh(x - y) == 0.3)
    m.addConstr(nlfunc.signpow(x, 2) <= 4)

    m.setObjective(x + y, GRB.MAXIMIZE)

    # 全局最优（默认，空间 B&B）
    m.optimize()
    if m.Status == GRB.OPTIMAL:
        print(f"全局最优: x={x.X:.4f}, y={y.X:.4f}, obj={m.ObjVal:.4f}")


def nl_barrier_example():
    """
    大规模 NLP 用 NL Barrier 找局部最优（13.0）。
    示例：几何规划风格。
    """
    m = gp.Model("nlp_barrier")
    n = 5
    x = m.addVars(n, lb=0.1, ub=10, name="x")

    # 约束：sum log(x_i) >= 1
    m.addConstr(gp.quicksum(nlfunc.log(x[i]) for i in range(n)) >= 1)

    # 目标：最小化 sum x_i * exp(-x_i)
    obj = m.addVar(lb=-GRB.INFINITY, name="obj")
    m.addConstr(obj == gp.quicksum(x[i] * nlfunc.exp(-x[i]) for i in range(n)))
    m.setObjective(obj, GRB.MINIMIZE)

    # 启用 NL Barrier
    m.Params.OptimalityTarget = 1
    m.Params.NLBarIterLimit = 500
    m.optimize()

    if m.Status in (GRB.OPTIMAL, GRB.LOCALLY_OPTIMAL):
        print("局部最优:")
        for i in range(n):
            print(f"  x[{i}] = {x[i].X:.4f}")
        print(f"目标: {m.ObjVal:.6f}")
        print(f"NL Barrier 迭代数: {m.NLBarIterCount}")


if __name__ == "__main__":
    print("--- 非线性回归 ---")
    nonlinear_regression()
    print("\n--- 非线性约束 Demo ---")
    nonlinear_constraint_example()
    print("\n--- NL Barrier ---")
    nl_barrier_example()
