function qh2dc_verify_run(outfile)
%QH2DC_VERIFY_RUN  Execute the full study and emit machine-readable results.
%
%   This is an execution harness, not a second model.  It calls exactly the
%   same functions as MAIN_QH2DC and writes every reported quantity to a flat
%   key=value file so that an external checker can compare actual output
%   against reference values without any number being retyped by hand.
%
%   It deliberately does NOT call QH2DC_WRITE_RESULTS, so the published
%   ../data/research_results_gridflex.csv is left untouched.
%
%   Usage:  matlab -batch "addpath('../matlab'); qh2dc_verify_run('run.txt')"

if nargin < 1, outfile = 'qh2dc_run_actual.txt'; end
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here, '..', 'matlab'));
old = cd(fullfile(here, '..', 'matlab'));
cleaner = onCleanup(@() cd(old));

fid = fopen(fullfile(here, outfile), 'w');
w = @(k, v) fprintf(fid, '%s=%.10g\n', k, v);

fprintf(fid, 'matlab_version=%s\n', version);
fprintf(fid, 'has_intlinprog=%d\n', ...
        double(exist('intlinprog','file')==2 || exist('intlinprog','builtin')==5));
fprintf(fid, 'has_glpk=%d\n', double(exist('glpk','file')>0 || exist('glpk','builtin')>0));

t_start = tic;
cfg = qh2dc_config();
B = qh2dc_load_benchmark(cfg);
J = qh2dc_jobs(cfg, B);
w('horizon_h', B.T);
w('n_bundles', J.n);
w('renewable_supply_MWh', sum(B.ren));

o_nohydro = struct('use_h2', false, 'flexible', false);
o_hydro   = struct('use_h2', true,  'flexible', false);
o_flex    = struct('use_h2', true,  'flexible', true);

S0 = struct('pg', B.load_base, 'pe', zeros(B.T,1), 'pf', zeros(B.T,1), ...
            'pc', zeros(B.T,1), 'h', zeros(B.T,1), 'ps', zeros(B.T,1), ...
            'sched', B.flex_base, 'delay', zeros(J.n,1), 'cap', inf(B.T,1));
M0 = qh2dc_metrics(cfg, B, J, S0); M0.ren_util_pct = 0;

S1 = qh2dc_dispatch(cfg, B, J, inf, o_nohydro);
qh2dc_assert_feasible(S1, 'R1'); M1 = qh2dc_metrics(cfg, B, J, S1);

[c2, S2] = qh2dc_min_capacity(cfg, B, J, o_hydro);
qh2dc_assert_feasible(S2, 'R2');
M2 = qh2dc_metrics(cfg, B, J, S2, c2);
S2u = qh2dc_dispatch(cfg, B, J, inf, o_hydro);   % Fig. 5 counterfactual

[c3, S3] = qh2dc_min_capacity(cfg, B, J, o_flex);
M3 = qh2dc_metrics(cfg, B, J, S3, c3);

S4 = qh2dc_dispatch(cfg, B, J, B.cap_nonfirm, o_flex);
qh2dc_assert_feasible(S4, 'R4'); M4 = qh2dc_metrics(cfg, B, J, S4);

S5 = qh2dc_dispatch(cfg, B, J, B.cap_phased, o_flex);
qh2dc_assert_feasible(S5, 'R5'); M5 = qh2dc_metrics(cfg, B, J, S5);

fprintf(fid, 'solver_used=%s\n', S1.solver);

Ms = {M0, M1, M2, M3, M4, M5};
C0 = M0.conn_MW;
for i = 1:numel(Ms)
    m = Ms{i}; tag = sprintf('R%d', i-1);
    w([tag '_conn_MW'],     m.conn_MW);
    w([tag '_red_pct'],     100 * (1 - m.conn_MW / C0));
    w([tag '_grid_MWh'],    m.grid_MWh);
    w([tag '_co2_t'],       m.co2_t);
    w([tag '_ren_util_pct'],m.ren_util_pct);
    w([tag '_avg_delay_h'], m.avg_delay_h);
    w([tag '_max_delay_h'], m.max_delay_h);
    w([tag '_shifted_pct'], m.shifted_pct);
    w([tag '_viol_MWh'],    m.viol_MWh);
    w([tag '_shed_MWh'],    m.shed_MWh);
end

w('R1_curt_MWh', M1.curt_MWh);
w('R2_el_MWh',   M2.el_MWh);
w('R2_peak_import_MW', max(S2.pg));
w('R2_fc_MWh',   M2.fc_MWh);

% ---- model invariants ---------------------------------------------------
% These must hold for ANY valid solution, on either solver path.  They are
% emitted so the external checker can fail loudly rather than relying on a
% comparison against reference numbers that only exists for the MILP path.
onehot_ok = 1; inv_ok = 1; cap_ok = 1;
for Sx = {S1, S2, S3, S4, S5}
    Z = Sx{1};
    % exactly one slot per bundle (S.sel indexes the chosen candidate)
    if numel(Z.sel) ~= J.n || any(Z.sel < 1) || any(Z.sel > J.K)
        onehot_ok = 0;
    end
    % inventory within bounds at every hour
    if any(Z.h < -1e-6) || any(Z.h > cfg.H_max + 1e-6)
        inv_ok = 0;
    end
    % import never above the envelope it was solved against
    if any(Z.pg > Z.cap + 1e-6)
        cap_ok = 0;
    end
end
w('inv_onehot_ok',        onehot_ok);
w('inv_inventory_ok',     inv_ok);
w('inv_cap_respected_ok', cap_ok);
w('inv_h2_terminal_err',  abs(S2.h(end) - cfg.H_final));
w('inv_max_shed_MWh',     max([M1.shed_MWh, M2.shed_MWh, M3.shed_MWh, ...
                               M4.shed_MWh, M5.shed_MWh]));
w('inv_R2_peak_vs_cap',   abs(max(S2.pg) - c2));

% hydrogen inventory checks
w('h2_terminal_MWh',  S2.h(end));
w('h2_max_inventory', max(S2.h));
w('h2_min_inventory', min(S2.h));

% R4 without workload flexibility: expected to be infeasible
S4n = qh2dc_dispatch(cfg, B, J, B.cap_nonfirm, o_hydro);
w('R4_pinned_infeasible', double(isempty(S4n)));
Sinf = qh2dc_dispatch(cfg, B, J, inf, o_hydro);
excess = max(0, Sinf.pg - B.cap_nonfirm);
w('R4_breach_hours',     sum(excess > 1e-6));
w('R4_breach_MWh',       sum(excess));
w('R4_breach_hours_48h', sum(excess(1:48) > 1e-6));

% ---- quantum block ----
Qs = qh2dc_qubo(cfg, B, J, cfg.qaoa.day);
BF = qh2dc_qubo_bruteforce(Qs);
w('qubo_n_vars',    Qs.n);
w('qubo_n_states',  BF.n_states);
w('qubo_n_feasible',BF.n_feasible);
w('qubo_best_cost', BF.best_cost);
for j = 1:numel(BF.best_hours)
    w(sprintf('qubo_best_hour_%d', j), BF.best_hours(j));
end
for i = 1:numel(cfg.qaoa.depths)
    p = cfg.qaoa.depths(i);
    QA = qh2dc_qaoa(cfg, Qs, BF, p);
    tag = sprintf('qaoa_p%d', p);
    w([tag '_expect'],    QA.expect);
    w([tag '_feas_mass'], QA.feas_mass);
    w([tag '_p_optimal'], QA.p_optimal);
    w([tag '_match'],     double(QA.matches_exact));
    w([tag '_gap'],       QA.gap);
end

% ---- figures ----
figdir = cfg.paths.figures;
if exist(figdir, 'dir') ~= 7, mkdir(figdir); end
QA1 = qh2dc_qaoa(cfg, Qs, BF, 1);
qh2dc_figures(cfg, B, J, struct('S1', S1, 'S2', S2, 'S2u', S2u, 'S4', S4), Ms, ...
              {'R0','R1','R2','R3','R4','R5'}, Qs, BF, QA1);
for k = 1:6
    for ext = {'pdf', 'png'}
        f = fullfile(figdir, sprintf('gr%d.%s', k, ext{1}));
        d = dir(f);
        if isempty(d)
            fprintf(fid, 'fig_gr%d_%s_bytes=0\n', k, ext{1});
        else
            fprintf(fid, 'fig_gr%d_%s_bytes=%d\n', k, ext{1}, d.bytes);
        end
    end
end

w('runtime_s', toc(t_start));
fprintf(fid, 'status=COMPLETED\n');
fclose(fid);
fprintf('verification run complete -> %s\n', fullfile(here, outfile));
end
