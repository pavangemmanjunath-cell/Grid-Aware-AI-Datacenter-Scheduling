function S = qh2dc_fallback_dispatch(cfg, B, J, cap, opt)
%QH2DC_FALLBACK_DISPATCH  Toolbox-free scheduler used when no MILP solver
%   is installed.  It reproduces the structure of the MILP solution with two
%   nested rules instead of a branch-and-bound search:
%
%     1. Placement.  Bundles start in their baseline slot.  While any hour
%        breaches the envelope, the bundle whose relocation removes the most
%        exceedance for the least delay is moved.  This is a steepest-descent
%        local search over the same one-hot feasible set as the MILP.
%     2. Dispatch.  For a fixed placement, the electrolyser absorbs surplus
%        renewables up to its rating and the storage limit, and the fuel cell
%        discharges the resulting inventory, first where the envelope would
%        otherwise be breached and then at the highest-carbon hours, subject
%        to the terminal inventory constraint.
%
%   The capacity figures returned by this path agree with the MILP path to
%   within the bisection resolution on the benchmark; the energy and carbon
%   totals can differ marginally because the rules are greedy rather than
%   globally optimal.  The MILP path remains the reference.

T = B.T;
sel = ones(J.n, 1);                       % start from the baseline slots
S = local_dispatch(cfg, B, J, cap, sel, opt);

if opt.flexible
    for iter = 1:(J.n * J.K)
        exc = sum(max(0, S.pg - cap)) + sum(S.ps);
        if exc <= 1e-9, break; end
        % Steepest descent on envelope exceedance.  The comparison is
        % lexicographic: a move is preferred if it removes strictly more
        % exceedance, and added delay only breaks ties between moves that
        % remove the same amount.  Scoring the two into a single number
        % lets a small delay penalty veto the last, feasibility-restoring
        % move when the residual exceedance is smaller than that penalty.
        best = []; bestGain = -inf; bestDelay = inf; bestS = [];
        for j = 1:J.n
            for k = 1:J.K
                if k == sel(j), continue; end
                trial = sel; trial(j) = k;
                St = local_dispatch(cfg, B, J, cap, trial, opt);
                exc_t = sum(max(0, St.pg - cap)) + sum(St.ps);
                gain  = exc - exc_t;
                dDelay = max(0, J.delay(j, k) - J.delay(j, sel(j)));
                better = (gain > bestGain + 1e-12) || ...
                         (abs(gain - bestGain) <= 1e-12 && dDelay < bestDelay);
                if better
                    bestGain = gain; bestDelay = dDelay;
                    best = [j k]; bestS = St; %#ok<AGROW>
                end
            end
        end
        if isempty(best) || bestGain <= 1e-9, break; end
        sel(best(1)) = best(2); S = bestS;
    end
end

if sum(max(0, S.pg - cap)) > 1e-6 || sum(S.ps) > 1e-6
    S = [];
    return;
end
S.sel = sel;
S.delay = arrayfun(@(j) J.delay(j, sel(j)), (1:J.n).');
S.cap = cap;
S.solver = 'fallback';
end

% ------------------------------------------------------------------------
function S = local_dispatch(cfg, B, J, cap, sel, opt)
T = B.T;
sched = zeros(T, 1);
for j = 1:J.n
    t = J.cand(j, sel(j)) + 1;
    sched(t) = sched(t) + J.P_MW(j);      % MW, not MWh
end
D  = B.fixed + sched;
net = D - B.ren;                             % >0 deficit, <0 surplus

EL = cfg.EL_max * opt.use_h2;
FC = cfg.FC_max * opt.use_h2;
HM = cfg.H_max  * opt.use_h2;
H0 = cfg.H_init * opt.use_h2;

pe = zeros(T,1); pf = zeros(T,1); pc = zeros(T,1); pg = zeros(T,1); h = zeros(T,1);

% ---- pass 1: electrolyser absorbs surplus renewables -------------------
hh = H0;
for t = 1:T
    if net(t) < 0
        surplus = -net(t);
        pe(t) = min([surplus, EL, (HM - hh) / (cfg.eta_EL * cfg.dt)]);
        pc(t) = surplus - pe(t);
        hh = hh + cfg.eta_EL * pe(t) * cfg.dt;
    end
    h(t) = hh;
end

% ---- pass 2: fuel cell, first for envelope relief, then for carbon -----
% priority 1: hours where the deficit exceeds the connection envelope
need = max(0, net - cap);
order1 = find(need > 0);
% priority 2: remaining hours ranked by descending carbon intensity
rest = setdiff((1:T).', order1);
[~, ix] = sort(B.ci(rest), 'descend');
order = [order1; rest(ix)];

% Discharging at hour t lowers the inventory over the whole tail t..T, so the
% budget available at t is bounded by two things: the inventory must stay
% non-negative at every later hour, AND it must still finish at H_final.
% Using min(h(t:T)) alone enforces only the first, which lets the tail of the
% week be drained below the terminal target - exactly the end-of-horizon
% gaming the H_final constraint exists to prevent.
% NOTE: this must be evaluated inline.  An anonymous function would capture
% h by value at creation time and would never see the discharges below, which
% makes the budget unbounded.
HF = cfg.H_final * opt.use_h2;

for m = 1:numel(order)
    t = order(m);
    if net(t) <= 0, continue; end
    budget = max(0, min(min(h(t:T)), h(T) - HF));
    avail = min([FC, net(t), budget * cfg.eta_FC / cfg.dt]);
    if m <= numel(order1)
        want = min(avail, need(t));
    else
        want = min(avail, budget * cfg.eta_FC / cfg.dt);
    end
    if want <= 1e-12, continue; end
    pf(t) = pf(t) + want;
    h(t:T) = h(t:T) - want * cfg.dt / cfg.eta_FC;
end

% ---- terminal inventory: discharge any residual above the target -------
% The budget above guarantees h(T) >= H_final, so only the surplus branch can
% ever trigger here.
resid = h(T) - cfg.H_final * opt.use_h2;
if resid > 1e-9
    % surplus hydrogen left over: discharge it at the highest-carbon hours
    [~, ix] = sort(B.ci, 'descend');
    for t = ix.'
        if resid <= 1e-9, break; end
        room = min([FC - pf(t), max(0, net(t) - pf(t))]);
        take = min([room, resid * cfg.eta_FC / cfg.dt]);
        if take <= 1e-12, continue; end
        pf(t) = pf(t) + take;
        h(t:T) = h(t:T) - take * cfg.dt / cfg.eta_FC;
        resid = h(T) - cfg.H_final * opt.use_h2;
    end
end

pg = max(0, net - pf);
ps = max(0, pg - cap);          % what the envelope cannot deliver
pg = min(pg, cap);

S = struct('pg', pg, 'pe', pe, 'pf', pf, 'pc', pc, 'h', h, 'ps', ps, ...
           'sched', sched, 'sel', sel);
end
