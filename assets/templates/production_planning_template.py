"""
生产计划优化模板（含雇佣/外包/库存/缺货）。
改编自《数学建模与数学规划》第 5 章算例。
"""
import gurobipy as gp
from gurobipy import GRB


class Instance:
    """生产计划参数容器。修改这些值以适配你的问题。"""
    def __init__(self):
        self.period_num = 7                    # 0..N，0 是初始状态
        self.raw_material_cost = 90            # 原料成本/件
        self.unit_product_time = 5             # 单件所需工时
        self.price = 300                       # 单价
        self.init_employee_num = 1000
        self.init_inventory = 15000
        self.normal_unit_salary = 30           # 正班工资/h
        self.overtime_unit_salary = 40         # 加班工资/h
        self.work_day_num = 20                 # 每月工作天数
        self.work_time_each_day = 8            # 每天工时
        self.overtime_upper_limit = 20         # 每人每月加班上限/h
        self.outsource_unit_cost = 200         # 外包单价
        self.unit_inventory_cost = 15          # 库存成本/件
        self.unit_shortage_cost = 35           # 缺货成本/件
        self.hire_cost = 5000
        self.fire_cost = 8000
        self.inventory_LB_of_last_month = 10000
        self.demand = [0, 20000, 40000, 42000, 35000, 19000, 18500]
        self.fixed_monthly_cost = 15000        # 月固定管理费


def build_and_solve(ins):
    T = list(range(1, ins.period_num))
    M = max(ins.demand)   # 最紧的 Big-M

    with gp.Env() as env, gp.Model(env=env, name="production") as m:
        # --- 决策变量 ---
        x = m.addVars(T, vtype=GRB.INTEGER, name="x")         # 生产量
        y = m.addVars(T, vtype=GRB.INTEGER, name="y")         # 外包量
        z = m.addVars(T, vtype=GRB.BINARY,  name="z")         # 是否缺货
        I = m.addVars([0] + T, vtype=GRB.INTEGER, name="I")   # 月末库存
        e = m.addVars(T, lb=-GRB.INFINITY,
                      vtype=GRB.INTEGER, name="e")            # 生产+库存-需求
        L = m.addVars(T, vtype=GRB.INTEGER, name="L")         # 缺货量
        H = m.addVars(T, vtype=GRB.INTEGER, name="H")         # 雇佣
        F = m.addVars(T, vtype=GRB.INTEGER, name="F")         # 解雇
        P = m.addVars([0] + T, vtype=GRB.INTEGER, name="P")   # 员工
        O = m.addVars(T, lb=0, name="O")                       # 加班时间
        S = m.addVars(T, vtype=GRB.INTEGER, name="S")         # 销售

        # --- 初始与边界 ---
        m.addConstr(I[0] == ins.init_inventory)
        m.addConstr(P[0] == ins.init_employee_num)
        m.addConstr(I[T[-1]] >= ins.inventory_LB_of_last_month)

        # --- 每月约束 ---
        for i in T:
            # 物料平衡
            m.addConstr(I[i-1] + x[i] + y[i] + e[i] == ins.demand[i],
                        name=f"bal_{i}")
            # 库存动态
            m.addConstr(I[i-1] + x[i] + y[i] - S[i] == I[i],
                        name=f"inv_{i}")
            # 销售
            m.addConstr(S[i] == ins.demand[i] - L[i],
                        name=f"sale_{i}")
            # 员工动态
            m.addConstr(P[i-1] + H[i] - F[i] == P[i],
                        name=f"emp_{i}")
            # 工时
            m.addConstr(
                ins.unit_product_time * x[i] <=
                ins.work_time_each_day * ins.work_day_num * P[i] + O[i],
                name=f"time_{i}"
            )
            m.addConstr(O[i] <= ins.overtime_upper_limit * P[i],
                        name=f"ot_{i}")

            # 缺货双向指示（e>0 ⇔ z=1 ⇔ L=e；否则 L=0）
            m.addConstr(e[i] - M * z[i] <= 0,                     name=f"z1_{i}")
            m.addConstr(-(e[i] - 1) - M * (1 - z[i]) <= 0,        name=f"z2_{i}")
            m.addConstr(L[i] - e[i] - M * (1 - z[i]) <= 0,        name=f"L1_{i}")
            m.addConstr(e[i] - L[i] - M * (1 - z[i]) <= 0,        name=f"L2_{i}")

        # --- 目标：最大化净收益 ---
        m.setObjective(
            gp.quicksum(
                ins.price * S[i]
                - ins.raw_material_cost * x[i]
                - ins.outsource_unit_cost * y[i]
                - ins.overtime_unit_salary * O[i]
                - P[i] * (ins.normal_unit_salary *
                          ins.work_time_each_day * ins.work_day_num)
                - ins.fixed_monthly_cost
                - ins.unit_inventory_cost * I[i]
                - ins.unit_shortage_cost * L[i]
                - ins.hire_cost * H[i]
                - ins.fire_cost * F[i]
                for i in T
            ),
            GRB.MAXIMIZE
        )

        # --- 求解 ---
        m.Params.TimeLimit = 300
        m.optimize()

        # --- 输出 ---
        if m.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) and m.SolCount > 0:
            print(f"\n最优净收益: {m.ObjVal:,.2f} 元\n")
            header = f"{'月':>3} {'生产':>8} {'外包':>8} {'缺货':>8} {'销售':>8} {'库存':>8} {'员工':>6} {'加班h':>8}"
            print(header)
            print("-" * len(header))
            print(f"{'0':>3} {'—':>8} {'—':>8} {'—':>8} {'—':>8} "
                  f"{int(I[0].X):>8} {int(P[0].X):>6} {'—':>8}")
            for i in T:
                print(
                    f"{i:>3} {int(x[i].X):>8} {int(y[i].X):>8} "
                    f"{int(L[i].X):>8} {int(S[i].X):>8} "
                    f"{int(I[i].X):>8} {int(P[i].X):>6} "
                    f"{O[i].X:>8.1f}"
                )
        else:
            print(f"求解失败: status={m.Status}")


if __name__ == "__main__":
    build_and_solve(Instance())
