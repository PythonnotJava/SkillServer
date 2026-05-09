"""
Gurobi 模型诊断工具：
- 查看模型统计
- 找极端系数
- IIS 诊断
- 解质量评估
"""
import gurobipy as gp
from gurobipy import GRB


def diagnose(model):
    """对模型做全方位体检"""
    print("=" * 60)
    print("模型诊断报告")
    print("=" * 60)

    # 1. 规模
    print(f"\n[规模]")
    print(f"  变量数: {model.NumVars} (二进制 {model.NumBinVars}, 整数 {model.NumIntVars})")
    print(f"  线性约束: {model.NumConstrs}")
    print(f"  SOS: {model.NumSOS}")
    print(f"  二次约束: {model.NumQConstrs}")
    print(f"  一般约束: {model.NumGenConstrs}")
    print(f"  非线性约束: {getattr(model, 'NumNLConstrs', 0)}")
    print(f"  非零系数: {model.NumNZs}")
    print(f"  类型: MIP={model.IsMIP} QP={model.IsQP} QCP={model.IsQCP} MultiObj={model.IsMultiObj}")

    # 2. 系数范围
    print(f"\n[系数范围]")
    model.printStats()

    # 3. 条件数（需要先求解）
    if model.Status in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        try:
            k = model.Kappa
            print(f"\n[条件数]")
            print(f"  Kappa ≈ {k:.2e}")
            if k > 1e10:
                print("  ⚠️ 条件数很大，可能有数值问题！")
        except gp.GurobiError:
            pass


def extreme_coeffs(model, top=5):
    """找最大/最小非零系数"""
    vals = []
    for c in model.getConstrs():
        row = model.getRow(c)
        for i in range(row.size()):
            coef = row.getCoeff(i)
            if coef != 0:
                vals.append((abs(coef), coef, c.ConstrName, row.getVar(i).VarName))
    vals.sort()

    print(f"\n最小 {top} 非零系数:")
    for v in vals[:top]:
        print(f"  |{v[1]:+.2e}|  {v[2]} × {v[3]}")
    print(f"最大 {top} 非零系数:")
    for v in vals[-top:]:
        print(f"  |{v[1]:+.2e}|  {v[2]} × {v[3]}")

    if vals:
        ratio = vals[-1][0] / vals[0][0] if vals[0][0] > 0 else float('inf')
        print(f"比值: {ratio:.2e}")
        if ratio > 1e9:
            print("  ⚠️ 系数比值过大，建议重新缩放")


def diagnose_infeasibility(model, write_iis="infeasible.ilp"):
    """对不可行模型诊断"""
    if model.Status not in (GRB.INFEASIBLE, GRB.INF_OR_UNBD):
        print("模型不是不可行状态")
        return

    if model.Status == GRB.INF_OR_UNBD:
        print("INF_OR_UNBD，重新求解以区分...")
        model.Params.DualReductions = 0
        model.optimize()

    if model.Status == GRB.INFEASIBLE:
        print("计算 IIS...")
        model.computeIIS()
        model.write(write_iis)
        print(f"IIS 写入 {write_iis}")

        iis_constr = [c.ConstrName for c in model.getConstrs() if c.IISConstr]
        iis_lb = [v.VarName for v in model.getVars() if v.IISLB]
        iis_ub = [v.VarName for v in model.getVars() if v.IISUB]

        print(f"\nIIS 约束 ({len(iis_constr)}): {iis_constr[:10]}{'...' if len(iis_constr) > 10 else ''}")
        print(f"IIS LB 边界 ({len(iis_lb)}): {iis_lb[:10]}")
        print(f"IIS UB 边界 ({len(iis_ub)}): {iis_ub[:10]}")


def solution_quality(model):
    """评估当前解的质量"""
    if model.Status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL, GRB.TIME_LIMIT):
        return
    print("\n[解质量]")
    model.printQuality()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python gurobi_diagnostic.py <model.mps/lp/rew>")
        sys.exit(1)
    m = gp.read(sys.argv[1])
    diagnose(m)
    extreme_coeffs(m)
    m.optimize()
    solution_quality(m)
    diagnose_infeasibility(m)
