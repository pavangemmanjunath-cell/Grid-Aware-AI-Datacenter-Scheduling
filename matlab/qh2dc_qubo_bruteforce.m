function R = qh2dc_qubo_bruteforce(Qs)
%QH2DC_QUBO_BRUTEFORCE  Exact enumeration of the 2^n basis states.
%   With n = 12 this costs milliseconds and gives the reference against
%   which the QAOA output is judged.  It is a verification device, not part
%   of the proposed method.

n = Qs.n; Nst = 2^n;
bits = zeros(Nst, n);
for b = 1:n
    bits(:, b) = bitget((0:Nst-1).', b);
end
R.cost = sum((bits * Qs.Q) .* bits, 2) + Qs.const;
oh = true(Nst, 1);
for j = 1:Qs.n_jobs
    cols = (j-1)*Qs.K + (1:Qs.K);
    oh = oh & (sum(bits(:, cols), 2) == 1);
end
R.feasible = oh;
R.bits = bits;
fi = find(oh);
[R.best_cost, m] = min(R.cost(fi));
R.best_state = fi(m);
R.n_feasible = numel(fi);
R.n_states = Nst;
sel = zeros(Qs.n_jobs, 1);
for j = 1:Qs.n_jobs
    cols = (j-1)*Qs.K + (1:Qs.K);
    [~, sel(j)] = max(bits(R.best_state, cols));
end
R.best_sel = sel;
R.best_hours = arrayfun(@(j) Qs.cand(j, sel(j)), (1:Qs.n_jobs).');
end
