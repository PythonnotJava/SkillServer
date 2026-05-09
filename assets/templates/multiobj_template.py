"""
多目标优化模板：分层 + 混合结合。
场景：工作人员排班
  优先级 1：最小化未覆盖班次 (刚性)
  优先级 2：最小化工资总额 (次要)，允许前者退化 10%
"""
import gurobipy as gp
from gurobipy import GRB


def multiobj_schedule():
    workers = ['Amy', 'Bob', 'Cat', 'Dan', 'Eve']
    shifts = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

    wage = {'Amy': 10, 'Bob': 12, 'Cat': 11, 'Dan': 13, 'Eve': 9}
    demand = {'Mon': 3, 'Tue': 2, 'Wed': 4, 'Thu': 3, 'Fri': 2}

    # 不可用：工人在某天不能工作
    unavail = {('Amy', 'Wed'), ('Dan', 'Fri'), ('Eve', 'Mon')}

    with gp.Env() as env, gp.Model(env=env, name="multiobj") as m:
        x = m.addVars(workers, shifts, vtype=GRB.BINARY, name="x")

        # 禁用不可用班次
        for w, s in unavail:
            x[w, s].UB = 0

        # slack：每班未覆盖人数
        slack = m.addVars(shifts, lb=0, name="slack")

        # 需求约束（带 slack）
        m.addConstrs(
            (x.sum('*', s) + slack[s] >= demand[s] for s in shifts),
            name="demand"
        )

        # 每人每周最多 4 班
        m.addConstrs(
            (x.sum(w, '*') <= 4 for w in workers),
            name="maxshifts"
        )

        # 多目标
        m.ModelSense = GRB.MINIMIZE
        m.NumObj = 2

        # 目标 0：最小化总未覆盖 (高优先级)
        m.setObjectiveN(
            slack.sum(), index=0, priority=10, weight=1.0,
            abstol=0, reltol=0.1,      # 允许后续目标使此目标恶化 10%
            name="uncovered"
        )

        # 目标 1：最小化工资 (低优先级)
        m.setObjectiveN(
            gp.quicksum(wage[w] * x[w, s] for w in workers for s in shifts),
            index=1, priority=1, weight=1.0, name="wage"
        )

        m.optimize()

        if m.Status == GRB.OPTIMAL:
            # 查询每个目标值
            for i in range(m.NumObj):
                m.Params.ObjNumber = i
                print(f"Obj {i} ({m.getAttr('ObjNName')}): {m.ObjNVal:.2f}")

            print("\n排班:")
            for s in shifts:
                assigned = [w for w in workers if x[w, s].X > 0.5]
                uncov = int(slack[s].X + 0.5)
                print(f"  {s}: {assigned} (need={demand[s]}, uncovered={uncov})")


if __name__ == "__main__":
    multiobj_schedule()
