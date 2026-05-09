"""
Gurobi 回调模板：
1. 进度监控
2. 自定义终止（找到首个可行解后 60 秒停）
3. Lazy constraint 示例（框架，TSP 子环消除见 tsp_template.py）
"""
import time
import gurobipy as gp
from gurobipy import GRB


def mycallback(model, where):
    """通用回调：监控进度 + 自定义终止"""
    if where == GRB.Callback.MIP:
        # 周期性 MIP 进度
        nodecnt = model.cbGet(GRB.Callback.MIP_NODCNT)
        objbst = model.cbGet(GRB.Callback.MIP_OBJBST)
        objbnd = model.cbGet(GRB.Callback.MIP_OBJBND)
        solcnt = model.cbGet(GRB.Callback.MIP_SOLCNT)

        # 自定义终止 1：差距 < 10% 就停
        if solcnt > 0 and abs(objbst - objbnd) < 0.1 * (1.0 + abs(objbst)):
            print("提前终止：gap < 10%")
            model.terminate()

        # 自定义终止 2：节点数超阈值
        if nodecnt >= 100000 and solcnt > 0:
            print("提前终止：节点数超限")
            model.terminate()

    elif where == GRB.Callback.MIPSOL:
        # 新找到整数解
        obj = model.cbGet(GRB.Callback.MIPSOL_OBJ)
        nodecnt = model.cbGet(GRB.Callback.MIPSOL_NODCNT)
        print(f"新解: obj={obj:.4f} at node {nodecnt}")

        # 记录找到首个解的时间
        if not hasattr(model, '_first_sol_time'):
            model._first_sol_time = time.time()
            print("记录首解时间，60s 后自动停止")

    elif where == GRB.Callback.MIPNODE:
        # 节点 LP 松弛处理
        status = model.cbGet(GRB.Callback.MIPNODE_STATUS)
        if status == GRB.OPTIMAL:
            # 可在此注入启发式解或添加 user cut
            pass

    # 时间判断（所有 where 中都可以）
    if hasattr(model, '_first_sol_time'):
        if time.time() - model._first_sol_time > 60:
            model.terminate()


# Lazy constraint 示例框架
def lazy_callback(model, where):
    """假设 model._x 存储变量字典，在找到整数解时检查某逻辑约束"""
    if where == GRB.Callback.MIPSOL:
        vals = model.cbGetSolution(model._x)
        # 检查某条件，若违反则添加约束
        if some_condition_violated(vals):
            model.cbLazy(some_gurobi_constraint)


def some_condition_violated(vals):
    # 占位：返回 True/False
    return False


def demo():
    """演示：用回调求解背包问题"""
    m = gp.Model("demo")
    n = 20
    x = m.addVars(n, vtype=GRB.BINARY, name="x")
    profit = [i * 3 + 2 for i in range(n)]
    weight = [i * 2 + 1 for i in range(n)]
    m.addConstr(gp.quicksum(weight[i] * x[i] for i in range(n)) <= 50)
    m.setObjective(gp.quicksum(profit[i] * x[i] for i in range(n)), GRB.MAXIMIZE)

    m.optimize(mycallback)
    print(f"\n最终: obj={m.ObjVal}")


if __name__ == "__main__":
    demo()
