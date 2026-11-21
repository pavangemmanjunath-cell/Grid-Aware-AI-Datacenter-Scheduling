function cfg = qh2dc_config()
%QH2DC_CONFIG  Central parameter set for the QH2DC grid-connection study.
%
%   Every number that appears in the paper is defined here.  Changing a value
%   here changes the whole experiment; nothing is hard-coded elsewhere.
%
%   Reference: "Grid-Connection-Aware Scheduling of AI Data Centres with
%   Green Hydrogen and Quantum-Assisted Workload Placement".

% ---- horizon -----------------------------------------------------------
cfg.T          = 168;        % simulation horizon [h]
cfg.dt         = 1.0;        % time step [h]

% ---- green hydrogen plant ---------------------------------------------
cfg.EL_max     = 4.0;        % electrolyser rated power [MW]
cfg.eta_EL     = 0.72;       % electrolyser efficiency  [MWh_H2 / MWh_e]
cfg.FC_max     = 2.0;        % fuel-cell rated power    [MW]
cfg.eta_FC     = 0.55;       % fuel-cell efficiency     [MWh_e / MWh_H2]
cfg.H_max      = 20.0;       % hydrogen storage energy capacity [MWh_H2]
cfg.H_init     = 5.0;        % initial inventory  [MWh_H2]
cfg.H_final    = 5.0;        % terminal inventory [MWh_H2]  (anti-gaming)

% ---- connection envelopes ---------------------------------------------
cfg.nonfirm_normal   = 10.7; % non-firm cap outside congestion [MW]
cfg.nonfirm_reduced  = 6.5;  % non-firm cap during congestion  [MW]
cfg.nonfirm_window   = [8 14];        % congested hours of the day (inclusive)
cfg.phased_levels    = [8.7 9.7 10.7];% phased connection stages [MW]
cfg.phased_stage_h   = 56;            % duration of each phased stage [h]

% ---- flexible AI workload ---------------------------------------------
cfg.flex_hours    = [6 8 11 14];  % baseline start hour of each daily bundle
cfg.cand_offsets  = [0 3 7];      % candidate slots, hours after the baseline
                                  % (offset 0 is always the baseline slot)

% ---- scheduling objective weights -------------------------------------
% The objective is scientific, not economic: no electricity price appears.
cfg.w_shed  = 1e4;   % unserved energy               (dominant penalty)
cfg.w_co2   = 1.0;   % operational carbon            [per tCO2]
cfg.w_curt  = 1.0;   % renewable curtailment         [per MWh]
cfg.w_cycle = 0.02;  % hydrogen cycling regulariser  [per MWh through H2]
cfg.w_delay = 5.0;   % workload delay                [per bundle-hour]

% ---- QUBO weights (daily workload-placement subproblem) ---------------
cfg.qubo.A_onehot  = 40.0;  % one-hot constraint penalty
cfg.qubo.w_stress  = 6.0;   % connection-headroom violation at a candidate hour
cfg.qubo.w_carbon  = 1.0;   % carbon of running the bundle in that hour
cfg.qubo.w_renew   = 1.5;   % reward for coincidence with surplus renewables
cfg.qubo.w_delay   = 0.30;  % deferral penalty
cfg.qubo.w_collide = 2.5;   % penalty for two bundles landing in the same hour

% ---- QAOA experiment ---------------------------------------------------
cfg.qaoa.day        = 1;    % benchmark day used for the daily subproblem
cfg.qaoa.depths     = [1 2];% circuit depths p to evaluate
cfg.qaoa.restarts   = 5;    % randomised classical initialisations
cfg.qaoa.seed       = 7;    % RNG seed for the restarts
cfg.qaoa.max_evals  = 600;  % classical optimiser budget per restart

% ---- capacity search ---------------------------------------------------
cfg.cap_search_lo   = 0.0;  % bisection lower bound [MW]
cfg.cap_search_hi   = 16.0; % bisection upper bound [MW]
cfg.cap_search_iter = 24;   % bisection iterations (~1e-6 MW resolution)

% ---- workload-to-power mapping (used only by qh2dc_ingest_trace) ------
cfg.power.P_idle_gpu   = 0.055;  % idle GPU power [MW per 1000 GPU-equivalents]
cfg.power.P_rated_gpu  = 0.400;  % rated GPU power [MW per 1000 GPU-equivalents]
cfg.power.overhead_IT  = 1.35;   % CPU/memory/network/storage multiplier
cfg.power.PUE          = 1.18;   % facility power usage effectiveness

% ---- input / output ----------------------------------------------------
cfg.paths.data     = fullfile('..','data');
cfg.paths.figures  = fullfile('..','figures');
cfg.benchmark_csv  = 'research_benchmark_168h.csv';
cfg.jobs_csv       = 'research_flexible_jobs.csv';
cfg.results_csv    = 'research_results_gridflex.csv';
cfg.rng_seed       = 20260430;   % seed of the synthetic benchmark generator
end
