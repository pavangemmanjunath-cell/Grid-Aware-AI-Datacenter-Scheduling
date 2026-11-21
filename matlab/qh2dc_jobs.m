function J = qh2dc_jobs(cfg, B)
%QH2DC_JOBS  Flexible AI workload table derived from the analytical table.
%
%   Every hour at which the baseline flexible profile is non-zero is treated
%   as one delay-tolerant bundle.  Each bundle keeps its energy but may be
%   executed in any of its candidate slots.  Offset 0 is the baseline slot,
%   so the baseline schedule is always inside the feasible set and every
%   reported delay is measured against it.
%
%   Fields of J:
%     n         number of bundles
%     t0        baseline hour of each bundle (0-based)      [n x 1]
%     P_MW      bundle power while it runs           [MW]   [n x 1]
%     E_MWh     bundle energy, P_MW * dt             [MWh]  [n x 1]
%
%   The distinction matters even though dt = 1 h makes the two numerically
%   equal on this benchmark.  A bundle occupies one hourly slot at a constant
%   power P_MW; the power balance is an instantaneous identity in MW and must
%   use P_MW, while carbon and energy accounting integrate over the slot and
%   must use E_MWh = P_MW * dt.  Conflating them is dimensionally wrong and
%   would silently break the model at any dt other than one hour.
%     cand      candidate hours (0-based)                   [n x K]
%     delay     delay of each candidate w.r.t. t0    [h]     [n x K]
%     release   earliest admissible hour                    [n x 1]
%     deadline  latest admissible hour                      [n x 1]

idx  = find(B.flex_base > 0);
J.n  = numel(idx);
J.t0 = B.hour(idx);
J.P_MW  = B.flex_base(idx);          % power while the bundle runs   [MW]
J.E_MWh = J.P_MW * cfg.dt;           % energy of the bundle          [MWh]
K    = numel(cfg.cand_offsets);
J.K  = K;
J.cand  = zeros(J.n, K);
J.delay = zeros(J.n, K);
for j = 1:J.n
    for k = 1:K
        J.cand(j, k)  = min(B.T - 1, J.t0(j) + cfg.cand_offsets(k));
        J.delay(j, k) = J.cand(j, k) - J.t0(j);
    end
end
J.release  = J.t0;
J.deadline = J.cand(:, end);
end
