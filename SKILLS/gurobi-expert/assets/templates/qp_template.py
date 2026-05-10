"""
QP / QCP 模板。投资组合优化（Markowitz 风险最小化）。
"""
import gurobipy as gp
from gurobipy import GRB


def portfolio_optimization():
    # 假数据
    assets = ['Bond', 'Stock', 'Gold', 'Cash']
    expected_return = {'Bond': 0.04, 'Stock': 0.12, 'Gold': 0.08, 'Cash': 0.02}
    # 协方差矩阵 (对称 PSD)
    sigma = {
        ('Bond', 'Bond'): 0.01,   ('Bond', 'Stock'): 0.008,
        ('Bond', 'Gold'): 0.002,  ('Bond', 'Cash'): 0.0,
        ('Stock', 'Stock'): 0.04, ('Stock', 'Gold'): 0.015,
        ('Stock', 'Cash'): 0.0,
        ('Gold', 'Gold'): 0.02,   ('Gold', 'Cash'): 0.0,
        ('Cash', 'Cash'): 0.0001,
    }
    for (i, j), v in list(sigma.items()):
        sigma[(j, i)] = v
    target_return = 0.07

    with gp.Env() as env, gp.Model(env=env, name="portfolio") as m:
        # 投资比例 ∈ [0, 1]
        x = m.addVars(assets, lb=0, ub=1, name="x")

        # 预算
        m.addConstr(x.sum() == 1, name="budget")
        # 目标收益率
        m.addConstr(
            gp.quicksum(expected_return[a] * x[a] for a in assets) >= target_return,
            name="min_return"
        )

        # 最小化方差 x' Σ x (凸二次目标)
        risk = gp.quicksum(sigma[a, b] * x[a] * x[b] for a in assets for b in assets)
        m.setObjective(risk, GRB.MINIMIZE)

        m.optimize()

        if m.Status == GRB.OPTIMAL:
            print(f"风险 (方差): {m.ObjVal:.6f}")
            print(f"波动率: {m.ObjVal ** 0.5:.4%}")
            for a in assets:
                if x[a].X > 1e-4:
                    print(f"  {a}: {x[a].X:.2%}")


# 非凸 QP 示例：若 Q 不 PSD
def nonconvex_qp_example():
    with gp.Env() as env, gp.Model(env=env, name="nonconvex") as m:
        x = m.addVar(lb=-10, ub=10, name="x")
        y = m.addVar(lb=-10, ub=10, name="y")

        # 非凸：x*y 在 Q 矩阵中是 indefinite
        m.setObjective(x*y - 2*x + y, GRB.MINIMIZE)
        m.addConstr(x + y >= 1)
        m.addConstr(x*x + y*y <= 25)   # 圆盘

        m.Params.NonConvex = 2   # 必须！否则报 Q not PSD
        m.optimize()
        print(f"x={x.X:.3f}, y={y.X:.3f}, obj={m.ObjVal:.3f}")


if __name__ == "__main__":
    portfolio_optimization()
    print("\n--- 非凸 QP ---")
    nonconvex_qp_example()
