"""
Gurobi MIP 标准模板。
修改 TODO 部分为你的实际问题。
"""
import gurobipy as gp
from gurobipy import GRB


def build_and_solve():
    # ------- 数据 -------
    # TODO: 替换为真实数据
    items = ['A', 'B', 'C', 'D']
    profit = {'A': 3, 'B': 5, 'C': 4, 'D': 6}
    weight = {'A': 2, 'B': 3, 'C': 4, 'D': 5}
    capacity = 8

    with gp.Env() as env, gp.Model(env=env, name="mip") as m:
        # ------- 参数 -------
        m.Params.TimeLimit = 300      # 5 分钟上限
        m.Params.MIPGap = 0.01        # 1% 差距即停
        m.Params.Threads = 0          # 自动
        # m.Params.MIPFocus = 1       # 1=找可行解, 2=证最优, 3=改进下界
        # m.Params.LogFile = "solve.log"

        # ------- 变量 -------
        x = m.addVars(items, vtype=GRB.BINARY, name="x")

        # ------- 约束 -------
        m.addConstr(
            gp.quicksum(weight[i] * x[i] for i in items) <= capacity,
            name="capacity"
        )

        # ------- 目标 -------
        m.setObjective(
            gp.quicksum(profit[i] * x[i] for i in items),
            GRB.MAXIMIZE
        )

        # ------- 求解 -------
        m.optimize()

        # ------- 状态检查 + 输出 -------
        if m.Status == GRB.OPTIMAL:
            print(f"最优解: {m.ObjVal}")
            for i in items:
                if x[i].X > 0.5:
                    print(f"  选 {i}")
        elif m.Status == GRB.TIME_LIMIT:
            print(f"超时. 当前目标值: {m.ObjVal}, gap: {m.MIPGap:.2%}")
        elif m.Status == GRB.INFEASIBLE:
            print("模型不可行，计算 IIS...")
            m.computeIIS()
            m.write("infeas.ilp")
        elif m.Status == GRB.UNBOUNDED:
            print("模型无界")
        else:
            print(f"状态: {m.Status}")


if __name__ == "__main__":
    build_and_solve()
