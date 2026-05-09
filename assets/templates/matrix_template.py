"""
Gurobi Matrix API (MVar) 模板。
高效构造大规模线性代数风格模型。
"""
import numpy as np
from scipy import sparse
import gurobipy as gp
from gurobipy import GRB


def matrix_lp():
    """
    LP:
        max c^T x
        s.t. A x <= b
             x >= 0
    """
    # 5 变量, 3 约束
    c = np.array([3, 2, 5, 4, 1])
    A = sparse.csr_matrix([
        [1, 2, 3, 1, 0],
        [2, 1, 1, 4, 2],
        [1, 0, 2, 1, 3],
    ])
    b = np.array([10, 15, 12])

    m = gp.Model("matrix_lp")
    x = m.addMVar(shape=5, lb=0, name="x")
    m.setObjective(c @ x, GRB.MAXIMIZE)
    m.addConstr(A @ x <= b, name="cap")
    m.optimize()

    print(f"Obj: {m.ObjVal}")
    print(f"x: {x.X}")


def nqueens(n=8):
    """N 皇后: 放置 n 个皇后互不攻击"""
    m = gp.Model("nqueens")
    X = m.addMVar((n, n), vtype=GRB.BINARY, name="Q")

    m.setObjective(X.sum(), GRB.MAXIMIZE)

    # 每行、每列至多一个
    m.addConstr(X.sum(axis=1) <= 1, name="row")
    m.addConstr(X.sum(axis=0) <= 1, name="col")

    # 对角线
    for k in range(-(n - 1), n):
        # 主对角
        diag_idx = [(i, i + k) for i in range(n)
                    if 0 <= i + k < n]
        if len(diag_idx) > 1:
            m.addConstr(gp.quicksum(X[i, j] for i, j in diag_idx) <= 1)
        # 反对角
        anti_idx = [(i, n - 1 - i + k) for i in range(n)
                    if 0 <= n - 1 - i + k < n]
        if len(anti_idx) > 1:
            m.addConstr(gp.quicksum(X[i, j] for i, j in anti_idx) <= 1)

    m.optimize()

    print(f"放置 {int(m.ObjVal)} 个皇后:")
    board = X.X
    for i in range(n):
        row = ""
        for j in range(n):
            row += "Q " if board[i, j] > 0.5 else ". "
        print(f"  {row}")


def portfolio_mvar():
    """Matrix 版投资组合"""
    np.random.seed(0)
    n = 5
    mu = np.random.rand(n) * 0.1 + 0.02
    # 随机生成 PSD 协方差
    L = np.random.randn(n, n) * 0.1
    Sigma = L @ L.T + np.eye(n) * 0.001

    m = gp.Model("port")
    x = m.addMVar(n, lb=0, ub=1)
    m.addConstr(x.sum() == 1)
    m.addConstr(mu @ x >= 0.05)
    m.setObjective(x @ Sigma @ x, GRB.MINIMIZE)
    m.optimize()
    print(f"min risk={m.ObjVal:.5f}, weights={x.X}")


if __name__ == "__main__":
    print("--- Matrix LP ---")
    matrix_lp()
    print("\n--- N-Queens 8x8 ---")
    nqueens(8)
    print("\n--- Portfolio (MVar) ---")
    portfolio_mvar()
