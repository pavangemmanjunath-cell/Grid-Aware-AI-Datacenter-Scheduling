"""Compare an actual MATLAB execution against the published reference artefacts.

Reference values are READ FROM the shipped files -- data/research_results_gridflex.csv
and data/verification_summary.json -- never retyped here.  Actual values are READ FROM
verify/qh2dc_run_actual.txt, which is written by qh2dc_verify_run.m during a real
MATLAB run.  Nothing in this file asserts what the answer should be; it only compares
two files and reports.

Usage:  python verify/check_run.py
"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
DAT = os.path.join(BASE, 'data')

ACTUAL_FILE = os.path.join(HERE, 'qh2dc_run_actual.txt')
if not os.path.exists(ACTUAL_FILE):
    sys.exit('No execution output found at %s.\n'
             'Run:  matlab -batch "qh2dc_verify_run(\'qh2dc_run_actual.txt\')"'
             % ACTUAL_FILE)

# ---------------------------------------------------------------- actual ----
actual = {}
for line in open(ACTUAL_FILE):
    if '=' not in line:
        continue
    k, v = line.strip().split('=', 1)
    try:
        actual[k] = float(v)
    except ValueError:
        actual[k] = v

if actual.get('status') != 'COMPLETED':
    sys.exit('Execution did not complete; refusing to report results.')

# ------------------------------------------------------------- reference ----
ref = {}
with open(os.path.join(DAT, 'research_results_gridflex.csv')) as fh:
    for i, row in enumerate(csv.DictReader(fh)):
        tag = 'R%d' % i
        ref[tag + '_grid_MWh']     = float(row['grid_energy_MWh'])
        ref[tag + '_conn_MW']      = float(row['connection_capacity_MW'])
        ref[tag + '_red_pct']      = float(row['capacity_reduction_pct'])
        ref[tag + '_co2_t']        = float(row['operational_CO2_t'])
        ref[tag + '_ren_util_pct'] = float(row['renewable_utilization_pct'])
        ref[tag + '_avg_delay_h']  = float(row['average_workload_delay_h'])
        ref[tag + '_shifted_pct']  = float(row['jobs_shifted_pct'])
        ref[tag + '_viol_MWh']     = float(row['violation_energy_MWh'])

vs = json.load(open(os.path.join(DAT, 'verification_summary.json')))
ref['qubo_n_states']   = vs['n_states']
ref['qubo_n_feasible'] = vs['n_feasible']
ref['qubo_best_cost']  = vs['best_energy']
for j, h in enumerate(vs['assignment_hours'], 1):
    ref['qubo_best_hour_%d' % j] = h
for p in ('1', '2'):
    q = vs['qaoa'][p]
    ref['qaoa_p%s_expect' % p]    = q['exp']
    ref['qaoa_p%s_feas_mass' % p] = q['feas_mass']
    ref['qaoa_p%s_p_optimal' % p] = q['p_opt']
    ref['qaoa_p%s_gap' % p]       = q['gap']
ref['R1_curt_MWh'] = vs['R1_curt']
ref['R2_el_MWh']   = vs['R2_EL']
ref['R2_fc_MWh']   = vs['R2_FC']
ref['R3_max_delay_h'] = vs['R3_maxdelay']
ref['R4_max_delay_h'] = vs['R4_maxdelay']
ref['R5_max_delay_h'] = vs['R5_maxdelay']

# ------------------------------------------------------------- groupings ----
GROUPS = [
    ('Connection capacity (the headline result)',
     ['R%d_conn_MW' % i for i in range(6)] + ['R%d_red_pct' % i for i in range(6)]),
    ('Workload flexibility',
     ['R%d_avg_delay_h' % i for i in range(6)] +
     ['R%d_shifted_pct' % i for i in range(6)] +
     ['R3_max_delay_h', 'R4_max_delay_h', 'R5_max_delay_h']),
    ('Envelope compliance',
     ['R%d_viol_MWh' % i for i in range(6)]),
    ('Energy, carbon and hydrogen',
     ['R%d_grid_MWh' % i for i in range(6)] +
     ['R%d_co2_t' % i for i in range(6)] +
     ['R%d_ren_util_pct' % i for i in range(6)] +
     ['R1_curt_MWh', 'R2_el_MWh', 'R2_fc_MWh']),
    ('QUBO exhaustive enumeration',
     ['qubo_n_states', 'qubo_n_feasible', 'qubo_best_cost'] +
     ['qubo_best_hour_%d' % j for j in range(1, 5)]),
    ('QAOA p=1', ['qaoa_p1_expect', 'qaoa_p1_feas_mass',
                  'qaoa_p1_p_optimal', 'qaoa_p1_gap']),
    ('QAOA p=2', ['qaoa_p2_expect', 'qaoa_p2_feas_mass',
                  'qaoa_p2_p_optimal', 'qaoa_p2_gap']),
]

RTOL, ATOL = 1e-3, 1e-6   # 0.1 % relative, or 1e-6 absolute


def compare(a, b):
    if abs(a - b) <= ATOL:
        return True, 0.0
    denom = max(abs(b), 1e-12)
    rel = abs(a - b) / denom
    return rel <= RTOL, rel * 100.0


print('=' * 78)
print('QH2DC EXECUTION VERIFICATION')
print('=' * 78)
print('MATLAB          : %s' % actual['matlab_version'])
print('intlinprog      : %s' % ('available' if actual['has_intlinprog'] else 'NOT INSTALLED'))
print('glpk            : %s' % ('available' if actual['has_glpk'] else 'not available'))
print('solver actually used : %s' % actual['solver_used'])
print('runtime         : %.1f s' % actual['runtime_s'])
print('reference       : data/research_results_gridflex.csv + verification_summary.json')
print('tolerance       : %.3g%% relative or %g absolute' % (RTOL * 100, ATOL))
print()

tot_pass = tot_fail = 0
group_status = []
for title, keys in GROUPS:
    rows, npass, nfail = [], 0, 0
    for k in keys:
        if k not in actual or k not in ref:
            continue
        ok, relpct = compare(actual[k], ref[k])
        rows.append((k, actual[k], ref[k], ok, relpct))
        if ok:
            npass += 1
        else:
            nfail += 1
    if not rows:
        continue
    verdict = 'PASS' if nfail == 0 else 'FAIL'
    group_status.append((title, verdict, npass, nfail))
    print('-' * 78)
    print('%-56s %s (%d/%d)' % (title, verdict, npass, npass + nfail))
    print('-' * 78)
    print('  %-24s %16s %16s  %8s' % ('quantity', 'actual', 'reference', 'result'))
    for k, a, b, ok, relpct in rows:
        mark = 'pass' if ok else 'FAIL %.2f%%' % relpct
        print('  %-24s %16.6f %16.6f  %8s' % (k, a, b, mark))
    print()
    tot_pass += npass
    tot_fail += nfail

# ---------------------------------------------------- execution-only facts ----
print('-' * 78)
print('Additional checks (no published reference to compare against)')
print('-' * 78)
extras = [
    ('horizon_h',              'benchmark horizon (h)'),
    ('n_bundles',              'delay-tolerant bundles'),
    ('qubo_n_vars',            'QUBO binary variables'),
    ('R4_pinned_infeasible',   'R4 infeasible without flexibility (1 = yes)'),
    ('R4_breach_hours',        'R4 breach hours over the week'),
    ('R4_breach_MWh',          'R4 breach energy (MWh)'),
    ('R4_breach_hours_48h',    'R4 breach hours in the first 48 h'),
    ('qaoa_p1_match',          'p=1 mode is the exact optimum (1 = yes)'),
    ('qaoa_p2_match',          'p=2 mode is the exact optimum (1 = yes)'),
    ('h2_terminal_MWh',        'H2 inventory at t=T (config requires 5.0)'),
    ('R3_shed_MWh',            'R3 unserved energy (MWh)'),
]
for k, label in extras:
    if k in actual:
        print('  %-46s %16.8g' % (label, actual[k]))
print()

print('-' * 78)
print('Model invariants (must hold on BOTH solver paths)')
print('-' * 78)
INV = [
    ('inv_onehot_ok',        1.0,  0,     'exactly one slot chosen per bundle'),
    ('inv_inventory_ok',     1.0,  0,     'H2 inventory within [0, H_max] every hour'),
    ('inv_cap_respected_ok', 1.0,  0,     'import never exceeds its own envelope'),
    ('inv_h2_terminal_err',  0.0,  1e-6,  'terminal H2 equals H_final'),
    ('inv_max_shed_MWh',     0.0,  1e-6,  'no unserved energy in any scenario'),
    ('inv_R2_peak_vs_cap',   0.0,  1e-6,  'R2 peak import equals its reported capacity'),
]
inv_fail = 0
for k, want, tol, label in INV:
    if k not in actual:
        print('  %-52s %s' % (label, 'NOT REPORTED'))
        continue
    ok = abs(actual[k] - want) <= tol
    if not ok:
        inv_fail += 1
    print('  %-52s %12.6g  %s' % (label, actual[k], 'ok' if ok else '*** VIOLATED ***'))
print()

print('-' * 78)
print('Figure artefacts written by this run')
print('-' * 78)
missing = []
for k in range(1, 7):
    pdf = actual.get('fig_gr%d_pdf_bytes' % k, 0)
    png = actual.get('fig_gr%d_png_bytes' % k, 0)
    ok = pdf > 0 and png > 0
    if not ok:
        missing.append(k)
    print('  gr%d   pdf %9d B   png %9d B   %s' % (k, pdf, png, 'ok' if ok else 'MISSING'))
print()

print('=' * 78)
for title, verdict, npass, nfail in group_status:
    print('  %-56s %s (%d/%d)' % (title, verdict, npass, npass + nfail))
print('=' * 78)
print('TOTAL: %d passed, %d failed, %d figures written'
      % (tot_pass, tot_fail, 6 - len(missing)))
if inv_fail:
    print('\n*** %d MODEL INVARIANT(S) VIOLATED - the solution is not valid, ***'
          % inv_fail)
    print('*** regardless of how it compares against the reference.        ***')
else:
    print('All model invariants hold.')
if tot_fail:
    print('\nFailures above are real divergences between this run and the published')
    print('reference. They are not suppressed. See PAPER_CODE_ALIGNMENT.md for the')
    print('diagnosis of each one.')
print('=' * 78)
