%MAIN_QH2DC  End-to-end driver for the grid-connection study.
%
%   Run this file from the "matlab" directory.  It executes, in order,
%     1. the data-engineering layer,
%     2. the six connection scenarios R0-R5,
%     3. the minimum-capacity bisections,
%     4. the daily QUBO and the ideal-state-vector QAOA experiment,
%     5. the six publication figures gr1-gr6,
%   and writes the results tables back into ../data.
%
%   Runtime is a few minutes with the Optimization Toolbox and a few tens of
%   seconds longer on the toolbox-free path.

clear; clc; close all;
fprintf('QH2DC grid-connection study\n');
fprintf('---------------------------\n');

cfg = qh2dc_config();
if exist(cfg.paths.figures, 'dir') ~= 7, mkdir(cfg.paths.figures); end

% ---- 1. data engineering ------------------------------------------------
B = qh2dc_load_benchmark(cfg);
J = qh2dc_jobs(cfg, B);
fprintf('Benchmark: %d h, %d flexible bundles, %.1f MWh renewable supply\n', ...
        B.T, J.n, sum(B.ren));

% ---- 2. scenarios -------------------------------------------------------
o_nohydro = struct('use_h2', false, 'flexible', false);
o_hydro   = struct('use_h2', true,  'flexible', false);
o_flex    = struct('use_h2', true,  'flexible', true);

% R0: grid-only reference, no local resources at all
S0 = struct('pg', B.load_base, 'pe', zeros(B.T,1), 'pf', zeros(B.T,1), ...
            'pc', zeros(B.T,1), 'h', zeros(B.T,1), 'ps', zeros(B.T,1), ...
            'sched', B.flex_base, 'delay', zeros(J.n,1), 'cap', inf(B.T,1));
M0 = qh2dc_metrics(cfg, B, J, S0); M0.ren_util_pct = 0;

% R1: renewables only
S1 = qh2dc_dispatch(cfg, B, J, inf, o_nohydro);
qh2dc_assert_feasible(S1, 'R1');
M1 = qh2dc_metrics(cfg, B, J, S1);

% R2: renewables + green hydrogen, minimum uniform connection
% The reported capacity and the reported energy/carbon must come from the SAME
% solution.  Taking the metrics from a cap = inf dispatch while quoting the
% capacity from the bisection describes an operating point that was never
% solved: its true peak import is 12.59 MW, not the 10.59 MW quoted.
[c2, S2] = qh2dc_min_capacity(cfg, B, J, o_hydro);
qh2dc_assert_feasible(S2, 'R2');
M2 = qh2dc_metrics(cfg, B, J, S2, c2);

% Counterfactual used only by Fig. 5: the hydrogen plant dispatched with an
% UNCONSTRAINED connection and the bundles pinned to their baseline slots,
% then replayed against the non-firm envelope.  This is what the top panel of
% Fig. 5 shows.  It is not the smallest envelope violation achievable by
% re-dispatching hydrogen alone - that minimisation is never solved here.
S2u = qh2dc_dispatch(cfg, B, J, inf, o_hydro);
qh2dc_assert_feasible(S2u, 'R2 unconstrained counterfactual');

% R3: hydrogen + workload flexibility, minimum uniform connection
[c3, S3] = qh2dc_min_capacity(cfg, B, J, o_flex);
M3 = qh2dc_metrics(cfg, B, J, S3, c3);

% R4: time-varying non-firm envelope
S4 = qh2dc_dispatch(cfg, B, J, B.cap_nonfirm, o_flex);
qh2dc_assert_feasible(S4, 'R4');
M4 = qh2dc_metrics(cfg, B, J, S4);

% R5: phased envelope
S5 = qh2dc_dispatch(cfg, B, J, B.cap_phased, o_flex);
qh2dc_assert_feasible(S5, 'R5');
M5 = qh2dc_metrics(cfg, B, J, S5);

lbl = {'R0 Grid-only reference', 'R1 Renewable supply', ...
       'R2 Green-H2 assisted', 'R3 H2 + workload flexibility', ...
       'R4 Non-firm connection envelope', 'R5 Phased connection envelope'};
Ms = {M0, M1, M2, M3, M4, M5};
C0 = M0.conn_MW;

fprintf('\n%-34s %9s %8s %8s %9s %8s %8s %8s\n', 'Scenario', 'GridMWh', ...
        'ConnMW', 'Red%', 'CO2 t', 'RenUt%', 'Delay h', 'Shift%');
rows = cell(numel(Ms), 1);
for i = 1:numel(Ms)
    m = Ms{i};
    m.red_pct = 100 * (1 - m.conn_MW / C0);
    Ms{i} = m;
    fprintf('%-34s %9.2f %8.3f %8.1f %9.2f %8.2f %8.3f %8.2f\n', lbl{i}, ...
            m.grid_MWh, m.conn_MW, m.red_pct, m.co2_t, m.ren_util_pct, ...
            m.avg_delay_h, m.shifted_pct);
end

qh2dc_write_results(cfg, lbl, Ms);

% ---- 3. hydrogen bookkeeping -------------------------------------------
fprintf('\nRenewable curtailed without H2 : %.2f MWh (%.2f%% utilisation)\n', ...
        M1.curt_MWh, M1.ren_util_pct);
fprintf('Electrolyser intake with H2    : %.2f MWh\n', M2.el_MWh);
fprintf('Fuel-cell output with H2       : %.2f MWh\n', M2.fc_MWh);
fprintf('Envelope violation energy R4/R5: %.3f / %.3f MWh\n', M4.viol_MWh, M5.viol_MWh);

% ---- 4. quantum workload-placement subproblem --------------------------
fprintf('\nDaily QUBO / QAOA experiment (day %d)\n', cfg.qaoa.day);
Qs = qh2dc_qubo(cfg, B, J, cfg.qaoa.day);
BF = qh2dc_qubo_bruteforce(Qs);
fprintf('  variables %d, basis states %d, feasible one-hot states %d\n', ...
        Qs.n, BF.n_states, BF.n_feasible);
fprintf('  exact best feasible cost %.4f at hours [%s]\n', ...
        BF.best_cost, num2str(BF.best_hours.'));
QA = cell(numel(cfg.qaoa.depths), 1);
for i = 1:numel(cfg.qaoa.depths)
    p = cfg.qaoa.depths(i);
    QA{i} = qh2dc_qaoa(cfg, Qs, BF, p);
    fprintf('  p=%d  <C>=%.3f  feasible mass %.2f%%  P(exact)=%.3f%%  match=%d  gap=%.4f\n', ...
            p, QA{i}.expect, QA{i}.feas_mass, QA{i}.p_optimal, ...
            QA{i}.matches_exact, QA{i}.gap);
end

% ---- 5. figures ---------------------------------------------------------
fprintf('\nRendering figures into %s\n', cfg.paths.figures);
qh2dc_figures(cfg, B, J, struct('S1', S1, 'S2', S2, 'S2u', S2u, 'S4', S4), ...
              Ms, lbl, Qs, BF, QA{1});
fprintf('Done.\n');
