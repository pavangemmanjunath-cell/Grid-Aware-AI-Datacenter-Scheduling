function S = qh2dc_dispatch(cfg, B, J, cap, opt)
%QH2DC_DISPATCH  Connection-constrained scheduler for the AI data centre.
%
%   S = QH2DC_DISPATCH(CFG, B, J, CAP, OPT) co-optimises
%       * placement of the delay-tolerant AI bundles (binary, one-hot), and
%       * grid import, electrolyser, fuel-cell and curtailment power
%         (continuous),
%   subject to the hourly power balance, the hydrogen inventory dynamics and
%   the connection envelope P_grid(t) <= CAP(t).
%
%   CAP  scalar or T x 1 vector of hourly connection limits [MW].  Use Inf
%        for an unconstrained connection.
%   OPT  struct with optional fields
%          .use_h2    (true)   enable the green-hydrogen plant
%          .flexible  (false)  allow bundles to leave their baseline slot
%          .solver    ('auto') 'auto' | 'intlinprog' | 'glpk' | 'fallback'
%          .verbose   (false)
%
%   S is empty ([]) when the instance is infeasible, which is exactly the
%   test used by the minimum-capacity bisection.
%
%   Solver policy: the Optimization Toolbox is used when it is available.
%   On a base MATLAB installation the toolbox-free path in
%   QH2DC_FALLBACK_DISPATCH is used instead, so the study runs end to end
%   without any add-on product.

if nargin < 5, opt = struct(); end
if ~isfield(opt, 'use_h2'),   opt.use_h2   = true;  end
if ~isfield(opt, 'flexible'), opt.flexible = false; end
if ~isfield(opt, 'solver'),   opt.solver   = 'auto'; end
if ~isfield(opt, 'verbose'),  opt.verbose  = false; end

T = B.T;
if isscalar(cap), cap = repmat(cap, T, 1); else, cap = cap(:); end

solver = opt.solver;
if strcmp(solver, 'auto')
    if exist('intlinprog', 'file') == 2 || exist('intlinprog', 'builtin') == 5
        solver = 'intlinprog';
    elseif exist('glpk', 'file') || exist('glpk', 'builtin')
        solver = 'glpk';
    else
        solver = 'fallback';
    end
end

if strcmp(solver, 'fallback')
    S = qh2dc_fallback_dispatch(cfg, B, J, cap, opt);
    return;
end

% ---------------------------------------------------------------- layout
% x = [ pg(1:T) ; pe(1:T) ; pf(1:T) ; pc(1:T) ; h(1:T) ; ps(1:T) ; z(1:nb) ]
nb  = J.n * J.K;
N   = 6 * T + nb;
ipg = 1:T;  ipe = T + (1:T);  ipf = 2*T + (1:T);
ipc = 3*T + (1:T);  ih = 4*T + (1:T);  ips = 5*T + (1:T);
iz  = 6*T + (1:nb);
zid = @(j, k) 6*T + (j - 1) * J.K + k;

EL = cfg.EL_max * opt.use_h2;
FC = cfg.FC_max * opt.use_h2;
HM = cfg.H_max  * opt.use_h2;
H0 = cfg.H_init * opt.use_h2;
HF = cfg.H_final * opt.use_h2;

% -------------------------------------------------- equality constraints
% (1) hourly power balance
%     pg - pe - pc + pf + ps  =  fixed - ren  +  sum_jk P_j z_jk   [MW]
rI = []; rJ = []; rV = [];
for t = 1:T
    rI = [rI; t; t; t; t; t];                       %#ok<AGROW>
    rJ = [rJ; ipg(t); ipe(t); ipc(t); ipf(t); ips(t)]; %#ok<AGROW>
    rV = [rV; 1; -1; -1; 1; 1];                     %#ok<AGROW>
end
for j = 1:J.n
    for k = 1:J.K
        t = J.cand(j, k) + 1;
        % power balance is an identity in MW, so this is bundle POWER
        rI = [rI; t]; rJ = [rJ; zid(j, k)]; rV = [rV; -J.P_MW(j)]; %#ok<AGROW>
    end
end
A1 = sparse(rI, rJ, rV, T, N);
b1 = B.fixed - B.ren;

% (2) hydrogen inventory dynamics
rI = []; rJ = []; rV = [];
for t = 1:T
    rI = [rI; t]; rJ = [rJ; ih(t)]; rV = [rV; 1];                    %#ok<AGROW>
    if t > 1
        rI = [rI; t]; rJ = [rJ; ih(t-1)]; rV = [rV; -1];             %#ok<AGROW>
    end
    rI = [rI; t]; rJ = [rJ; ipe(t)]; rV = [rV; -cfg.eta_EL * cfg.dt]; %#ok<AGROW>
    rI = [rI; t]; rJ = [rJ; ipf(t)]; rV = [rV; cfg.dt / cfg.eta_FC];  %#ok<AGROW>
end
A2 = sparse(rI, rJ, rV, T, N);
b2 = zeros(T, 1); b2(1) = H0;

% (3) one-hot placement
rI = []; rJ = []; rV = [];
for j = 1:J.n
    for k = 1:J.K
        rI = [rI; j]; rJ = [rJ; zid(j, k)]; rV = [rV; 1]; %#ok<AGROW>
    end
end
A3 = sparse(rI, rJ, rV, J.n, N);
b3 = ones(J.n, 1);

Aeq = [A1; A2; A3];
beq = [b1; b2; b3];

% ------------------------------------------------ inequality constraints
% electrolyser and curtailment are backed by instantaneous renewables
rI = []; rJ = []; rV = [];
for t = 1:T
    rI = [rI; t; t]; rJ = [rJ; ipe(t); ipc(t)]; rV = [rV; 1; 1]; %#ok<AGROW>
end
Aineq = sparse(rI, rJ, rV, T, N);
bineq = B.ren;

% --------------------------------------------------------------- bounds
lb = zeros(N, 1);
ub = inf(N, 1);
ub(ipg) = cap;
ub(ipe) = EL;
ub(ipf) = FC;
ub(ipc) = B.ren;
ub(ih)  = HM;
ub(ips) = inf;
ub(iz)  = 1;
lb(ih(T)) = HF; ub(ih(T)) = HF;
if ~opt.flexible
    for j = 1:J.n
        lb(zid(j, 1)) = 1; ub(zid(j, 1)) = 1;
        for k = 2:J.K, ub(zid(j, k)) = 0; end
    end
end

% ------------------------------------------------------------ objective
c = zeros(N, 1);
c(ipg) = cfg.w_co2 * B.ci * cfg.dt / 1000;   % tCO2
c(ipc) = cfg.w_curt * cfg.dt;                % curtailed MWh
c(ipe) = cfg.w_cycle * cfg.dt;               % hydrogen cycling
c(ipf) = cfg.w_cycle * cfg.dt;
c(ips) = cfg.w_shed * cfg.dt;                % unserved energy
for j = 1:J.n
    for k = 1:J.K
        c(zid(j, k)) = cfg.w_delay * J.delay(j, k);
    end
end

% ---------------------------------------------------------------- solve
switch solver
    case 'intlinprog'
        o = optimoptions('intlinprog', 'Display', 'off', ...
                         'RelativeGapTolerance', 0, 'IntegerTolerance', 1e-6);
        [x, ~, flag] = intlinprog(c, iz, Aineq, bineq, Aeq, beq, lb, ub, o);
        ok = (flag == 1) && ~isempty(x);
    case 'glpk'
        vtype = repmat('C', N, 1); vtype(iz) = 'I';   % binary via 0/1 bounds
        ctype = [repmat('S', 2*T + J.n, 1); repmat('U', T, 1)];
        [x, ~, status] = glpk(c, [Aeq; Aineq], [beq; bineq], lb, ub, ctype, vtype, 1);
        ok = any(status == [0 5 2]) && ~isempty(x);
    otherwise
        error('qh2dc:solver', 'Unknown solver "%s".', solver);
end

if ~ok
    S = [];
    return;
end

% -------------------------------------------------------------- unpack
S.pg = x(ipg); S.pe = x(ipe); S.pf = x(ipf);
S.pc = x(ipc); S.h  = x(ih);  S.ps = x(ips);
Z = reshape(x(iz), J.K, J.n).';
S.sel   = zeros(J.n, 1);
S.delay = zeros(J.n, 1);
S.sched = zeros(T, 1);
for j = 1:J.n
    [~, k] = max(Z(j, :));
    S.sel(j)   = k;
    S.delay(j) = J.delay(j, k);
    S.sched(J.cand(j, k) + 1) = S.sched(J.cand(j, k) + 1) + J.P_MW(j);
end
S.cap    = cap;
S.solver = solver;

% ---- feasibility gate: no unserved energy is tolerated in this study ---
if sum(S.ps) > 1e-6
    S = [];
end
end
