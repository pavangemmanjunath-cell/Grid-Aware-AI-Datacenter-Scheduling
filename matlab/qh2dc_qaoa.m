function R = qh2dc_qaoa(cfg, Qs, BF, p)
%QH2DC_QAOA  Ideal state-vector QAOA on the daily placement QUBO.
%
%   The circuit is the standard alternating operator ansatz: a diagonal cost
%   phase exp(-i*gamma*C) followed by a transverse-field mixer, repeated p
%   times, starting from the uniform superposition.  The state vector is
%   simulated exactly, so the result is free of shot noise and of hardware
%   error; it tests the decomposition, not a quantum processor.
%
%   The classical outer loop uses FMINSEARCH, which ships with base MATLAB,
%   from cfg.qaoa.restarts randomised starting angles.

if nargin < 4, p = 1; end
n = Qs.n; Nst = 2^n;
cost  = BF.cost;
scale = max(abs(cost));
cs    = cost / scale;

rand('seed', cfg.qaoa.seed); %#ok<RAND>
best = struct('f', inf, 'par', []);
o = optimset('Display', 'off', 'MaxFunEvals', cfg.qaoa.max_evals, ...
             'MaxIter', cfg.qaoa.max_evals, 'TolX', 1e-6, 'TolFun', 1e-8);
for r = 1:cfg.qaoa.restarts
    x0 = pi * rand(2*p, 1);
    [xo, fo] = fminsearch(@(x) local_expect(x, p, cs, cost, n), x0, o);
    if fo < best.f, best.f = fo; best.par = xo; end
end

psi = local_state(best.par, p, cs, n);
pr  = abs(psi).^2;
R.p         = p;
R.params    = best.par;
R.expect    = best.f;
R.prob      = pr;
R.feas_mass = 100 * sum(pr(BF.feasible));
R.p_optimal = 100 * pr(BF.best_state);
fi = find(BF.feasible);
[~, m] = max(pr(fi));
R.top_feasible_state = fi(m);
R.matches_exact = (R.top_feasible_state == BF.best_state);
R.gap = abs(BF.cost(R.top_feasible_state) - BF.best_cost);
end

% ------------------------------------------------------------------------
function f = local_expect(x, p, cs, cost, n)
psi = local_state(x, p, cs, n);
f = real(sum(abs(psi).^2 .* cost));
end

function psi = local_state(x, p, cs, n)
Nst = 2^n;
psi = ones(Nst, 1) / sqrt(Nst);
g = x(1:p); b = x(p+1:2*p);
for i = 1:p
    psi = psi .* exp(-1i * g(i) * cs);         % cost phase (diagonal)
    c = cos(b(i)); s = -1i * sin(b(i));        % RX(2*beta) on every qubit
    for qb = 0:(n-1)
        m = bitshift(1, qb);
        i0 = find(bitand((0:Nst-1).', m) == 0) ;
        i1 = i0 + m;
        a0 = psi(i0); a1 = psi(i1);
        psi(i0) = c * a0 + s * a1;
        psi(i1) = s * a0 + c * a1;
    end
end
end
