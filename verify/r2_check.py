"""Quantify the R2 inconsistency using the true MILP (scipy.optimize.milp).

main_qh2dc.m reports R2 as the capacity from a bisection (c2) combined with the
energy/carbon metrics of a DIFFERENT solution (S2, dispatched with cap = inf).
This script solves both and prints them side by side so the size of the
discrepancy is measured rather than asserted.
"""
import numpy as np, pandas as pd, scipy.sparse as sp, os
from scipy.optimize import milp, LinearConstraint, Bounds

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.read_csv(os.path.join(BASE, 'data', 'research_benchmark_168h.csv'))
T = len(d)
FIX = d.fixed_ai_load_MW.values
FLX = d.baseline_flexible_load_MW.values
REN = d.renewable_MW.values
CI  = d.grid_carbon_kgCO2_per_MWh.values
ELM, ETA_EL, FCM, ETA_FC, HMAX, H0, HF = 4.0, 0.72, 2.0, 0.55, 20.0, 5.0, 5.0
W_CO2, W_CURT, W_CYC, W_SHED = 1.0, 1.0, 0.02, 1e4

# placement pinned to baseline (R2 has no workload flexibility)
sched = FLX.copy()

def solve(cap):
    """6T continuous vars: pg, pe, pf, pc, h, ps."""
    N = 6 * T
    S = lambda k: slice(k * T, (k + 1) * T)
    r, c, v = [], [], []
    for t in range(T):
        for k, val in [(0, 1.), (1, -1.), (2, 1.), (3, -1.), (5, 1.)]:
            r.append(t); c.append(k * T + t); v.append(val)
    A1 = sp.coo_matrix((v, (r, c)), shape=(T, N)); b1 = FIX + sched - REN
    r, c, v = [], [], []
    for t in range(T):
        r.append(t); c.append(4 * T + t); v.append(1.)
        if t > 0:
            r.append(t); c.append(4 * T + t - 1); v.append(-1.)
        r.append(t); c.append(1 * T + t); v.append(-ETA_EL)
        r.append(t); c.append(2 * T + t); v.append(1. / ETA_FC)
    A2 = sp.coo_matrix((v, (r, c)), shape=(T, N)); b2 = np.zeros(T); b2[0] = H0
    r, c, v = [], [], []
    for t in range(T):
        r += [t, t]; c += [1 * T + t, 3 * T + t]; v += [1., 1.]
    A3 = sp.coo_matrix((v, (r, c)), shape=(T, N))

    lo = np.zeros(N); hi = np.full(N, np.inf)
    hi[S(0)] = cap; hi[S(1)] = ELM; hi[S(2)] = FCM; hi[S(3)] = REN; hi[S(4)] = HMAX
    lo[4 * T + T - 1] = HF; hi[4 * T + T - 1] = HF
    cst = np.zeros(N)
    cst[S(0)] = W_CO2 * CI / 1000.
    cst[S(3)] = W_CURT
    cst[S(1)] = W_CYC; cst[S(2)] = W_CYC
    cst[S(5)] = W_SHED
    res = milp(cst, constraints=[LinearConstraint(A1, b1, b1),
                                 LinearConstraint(A2, b2, b2),
                                 LinearConstraint(A3, -np.inf, REN)],
               bounds=Bounds(lo, hi))
    if not res.success:
        return None
    x = res.x
    if x[S(5)].sum() > 1e-6:
        return None
    return dict(pg=x[S(0)], pe=x[S(1)], pf=x[S(2)], pc=x[S(3)], h=x[S(4)], ps=x[S(5)])


def report(tag, s, cap_reported):
    pg = s['pg']
    print('%-42s' % tag)
    print('   connection reported   %12.6f MW' % cap_reported)
    print('   peak import           %12.6f MW' % pg.max())
    print('   grid energy           %12.6f MWh' % pg.sum())
    print('   CO2                   %12.6f t' % ((pg * CI).sum() / 1000))
    print('   curtailed             %12.6f MWh' % s['pc'].sum())
    print('   renewable utilisation %12.6f %%' % (100 * (1 - s['pc'].sum() / REN.sum())))
    print('   electrolyser intake   %12.6f MWh' % s['pe'].sum())
    print('   fuel-cell output      %12.6f MWh' % s['pf'].sum())
    print('   terminal H2           %12.6f MWh_H2' % s['h'][-1])
    print()


# bisection for the minimum uniform capacity, same settings as MATLAB
lo, hi = 0.0, 16.0
assert solve(hi) is not None
for _ in range(24):
    mid = 0.5 * (lo + hi)
    if solve(mid) is None:
        lo = mid
    else:
        hi = mid
c2 = hi

print('=' * 62)
print('R2 CONSISTENCY CHECK  (true MILP, scipy.optimize.milp)')
print('=' * 62)
print()
s_inf = solve(np.inf)
report('AS PUBLISHED: metrics from cap=inf dispatch,\n  capacity from a separate bisection', s_inf, c2)
s_c2 = solve(c2)
report('CORRECTED: metrics from the SAME solution\n  that achieves the reported capacity', s_c2, c2)

print('-' * 62)
print('Deltas introduced by the fix')
print('-' * 62)
for k, unit, f in [('grid', 'MWh', lambda s: s['pg'].sum()),
                   ('co2', 't', lambda s: (s['pg'] * CI).sum() / 1000),
                   ('ren_util', '%', lambda s: 100 * (1 - s['pc'].sum() / REN.sum())),
                   ('el', 'MWh', lambda s: s['pe'].sum()),
                   ('fc', 'MWh', lambda s: s['pf'].sum())]:
    a, b = f(s_inf), f(s_c2)
    print('  %-10s %12.6f -> %12.6f  (%+.6f %s)' % (k, a, b, b - a, unit))
