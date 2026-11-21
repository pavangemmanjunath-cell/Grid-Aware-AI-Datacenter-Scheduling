function qh2dc_write_results(cfg, lbl, Ms)
%QH2DC_WRITE_RESULTS  Write the scenario table to ../data as CSV.
f = fullfile(cfg.paths.data, cfg.results_csv);
fid = fopen(f, 'w');
fprintf(fid, ['scenario,grid_energy_MWh,connection_capacity_MW,' ...
              'capacity_reduction_pct,operational_CO2_t,renewable_utilization_pct,' ...
              'average_workload_delay_h,jobs_shifted_pct,violation_energy_MWh\n']);
for i = 1:numel(Ms)
    m = Ms{i};
    fprintf(fid, '%s,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g\n', ...
            lbl{i}, m.grid_MWh, m.conn_MW, m.red_pct, m.co2_t, ...
            m.ren_util_pct, m.avg_delay_h, m.shifted_pct, m.viol_MWh);
end
fclose(fid);
fprintf('Results written to %s\n', f);
end
