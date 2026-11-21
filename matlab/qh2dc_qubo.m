function Qs = qh2dc_qubo(cfg, B, J, day)
%QH2DC_QUBO  Connection-aware QUBO for the daily workload-placement block.
%
%   The continuous energy variables stay classical.  Only the discrete
%   placement of one day's delay-tolerant bundles is encoded, which keeps
%   the register small enough for exact verification: four bundles with
%   three candidate slots give 12 binary variables and 4096 basis states.
%
%   Cost of assigning bundle j to candidate k, before the one-hot penalty:
%     * connection stress  - how far the bundle pushes the hour past the
%                            headroom left by the non-firm envelope;
%     * carbon             - grid carbon of running the bundle in that hour;
%     * renewable reward   - coincidence with surplus on-site generation;
%     * delay              - hours of deferral;
%     * collision          - pairwise penalty when two bundles pick the same
%                            hour, which is what makes the problem quadratic
%                            rather than separable.

if nargin < 4, day = cfg.qaoa.day; end
sel = find(B.day == (day - 1) & B.flex_base > 0);
n_j = numel(sel);
K   = J.K;
n   = n_j * K;

t0 = B.hour(sel);
P  = B.flex_base(sel);            % bundle power [MW]
E  = P * cfg.dt;                  % bundle energy [MWh]
cand = zeros(n_j, K); dly = zeros(n_j, K);
for j = 1:n_j
    for k = 1:K
        cand(j, k) = min(B.T - 1, t0(j) + cfg.cand_offsets(k));
        dly(j, k)  = cand(j, k) - t0(j);
    end
end

Q = zeros(n, n);
const = 0;
vi = @(j, k) (j - 1) * K + k;
q = cfg.qubo;

for j = 1:n_j
    for k = 1:K
        t = cand(j, k) + 1;
        headroom = B.cap_nonfirm(t) - (B.fixed(t) - B.ren(t));
        % headroom and renewable surplus are POWER, so the stress and
        % coincidence terms compare against P.  Carbon integrates over the
        % slot, so it uses E.
        stress   = max(0, P(j) - headroom);
        carbon   = B.ci(t) * E(j) / 1000;
        renmatch = min(P(j), max(0, B.ren(t) - B.fixed(t)));
        i1 = vi(j, k);
        Q(i1, i1) = Q(i1, i1) + q.w_stress * stress + q.w_carbon * carbon ...
                              - q.w_renew * renmatch + q.w_delay * dly(j, k);
    end
end

% one-hot penalty  A*(sum_k z_jk - 1)^2
for j = 1:n_j
    for k = 1:K
        Q(vi(j,k), vi(j,k)) = Q(vi(j,k), vi(j,k)) - q.A_onehot;
        for l = (k+1):K
            Q(vi(j,k), vi(j,l)) = Q(vi(j,k), vi(j,l)) + 2 * q.A_onehot;
        end
    end
    const = const + q.A_onehot;
end

% pairwise collision between different bundles landing in the same hour
for j = 1:n_j
    for j2 = (j+1):n_j
        for k = 1:K
            for l = 1:K
                if cand(j, k) == cand(j2, l)
                    Q(vi(j,k), vi(j2,l)) = Q(vi(j,k), vi(j2,l)) ...
                        + q.w_collide * P(j) * P(j2) / 10;
                end
            end
        end
    end
end

Qs.Q = triu(Q);  Qs.const = const;  Qs.n = n;  Qs.n_jobs = n_j;  Qs.K = K;
Qs.cand = cand;  Qs.delay = dly;    Qs.t0 = t0;
Qs.P = P;  Qs.E = E;  Qs.day = day;
end
