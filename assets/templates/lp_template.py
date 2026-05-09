"""
Gurobi LP 标准模板（生产规划示例）。
"""
import gurobipy as gp
from gurobipy import GRB


def solve_lp():
    # 产品与资源
    products = ['P1', 'P2', 'P3']
    resources = ['R1', 'R2']

    profit = {'P1': 20, 'P2': 25, 'P3': 30}
    usage = {
        ('P1', 'R1'): 1, ('P1', 'R2'): 2,
        ('P2', 'R1'): 2, ('P2', 'R2'): 3,
        ('P3', 'R1'): 3, ('P3', 'R2'): 1,
    }
    available = {'R1': 100, 'R2': 80}

    with gp.Env() as env, gp.Model(env=env, name="lp") as m:
        # 参数：LP 通常默认就好
        # m.Params.Method = 2  # 内点法 (barrier)
        # m.Params.Method = 5  # PDHG (13.0+, 大规模 LP 尝试)

        x = m.addVars(products, lb=0, name="x")

        m.addConstrs(
            (gp.quicksum(usage[p, r] * x[p] for p in products) <= available[r]
             for r in resources),
            name="resource"
        )

        m.setObjective(
            gp.quicksum(profit[p] * x[p] for p in products),
            GRB.MAXIMIZE
        )

        m.optimize()

        if m.Status == GRB.OPTIMAL:
            print(f"最大利润: {m.ObjVal:.2f}")
            for p in products:
                if x[p].X > 1e-6:
                    print(f"  {p}: {x[p].X:.2f} (简约成本 RC={x[p].RC:.3f})")
            # 对偶信息
            print("\n资源影子价格：")
            for c in m.getConstrs():
                print(f"  {c.ConstrName}: Pi={c.Pi:.3f}, Slack={c.Slack:.3f}")


if __name__ == "__main__":
    solve_lp()
