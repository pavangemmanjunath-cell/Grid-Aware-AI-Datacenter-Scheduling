function M = qh2dc_metrics(cfg, B, J, S, cap_report)
%QH2DC_METRICS  Evaluation metrics of Table 2 in the paper.

if nargin < 5 || isempty(cap_report), cap_report = max(S.pg); end
M.grid_MWh      = sum(S.pg) * cfg.dt;
M.conn_MW       = cap_report;
M.co2_t         = sum(S.pg .* B.ci) * cfg.dt / 1000;
M.curt_MWh      = sum(S.pc) * cfg.dt;
M.ren_util_pct  = 100 * (1 - M.curt_MWh / (sum(B.ren) * cfg.dt));
M.el_MWh        = sum(S.pe) * cfg.dt;
M.fc_MWh        = sum(S.pf) * cfg.dt;
M.viol_MWh      = sum(max(0, S.pg - S.cap)) * cfg.dt;
M.shed_MWh      = sum(S.ps) * cfg.dt;
M.avg_delay_h   = mean(S.delay);
M.max_delay_h   = max(S.delay);
M.shifted_pct   = 100 * mean(S.delay > 0);
M.sla_pct       = 100 * mean(S.delay <= (J.deadline - J.t0));
end
