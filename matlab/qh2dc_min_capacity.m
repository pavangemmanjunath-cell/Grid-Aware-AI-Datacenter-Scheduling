function [cmin, S] = qh2dc_min_capacity(cfg, B, J, opt)
%QH2DC_MIN_CAPACITY  Smallest uniform connection capacity that keeps the
%   data centre feasible with zero unserved energy.
%
%   The scheduler is monotone in the cap, so a bisection is exact up to the
%   requested resolution.  This is the quantity reported as the "required
%   connection capacity" for scenarios R2 and R3.

lo = cfg.cap_search_lo;
hi = cfg.cap_search_hi;
if isempty(qh2dc_dispatch(cfg, B, J, hi, opt))
    error('qh2dc:capSearch', 'Instance is infeasible even at the upper bound.');
end
for i = 1:cfg.cap_search_iter
    mid = 0.5 * (lo + hi);
    if isempty(qh2dc_dispatch(cfg, B, J, mid, opt))
        lo = mid;
    else
        hi = mid;
    end
end
cmin = hi;
S = qh2dc_dispatch(cfg, B, J, cmin, opt);
end
