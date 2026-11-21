function B = qh2dc_load_benchmark(cfg)
%QH2DC_LOAD_BENCHMARK  Data-engineering layer: build the analytical table.
%
%   B = QH2DC_LOAD_BENCHMARK(CFG) returns the hourly analytical table that
%   both the classical scheduler and the QUBO builder consume.  The shipped
%   CSV is used when it is present, so that the published numbers reproduce
%   bit-for-bit.  If the CSV is missing, an equivalent benchmark is generated
%   from the deterministic generator in QH2DC_BUILD_BENCHMARK.
%
%   Fields of B (all column vectors of length cfg.T unless stated):
%     hour        0-based hour index of the benchmark
%     day         0-based day index
%     hod         hour of day
%     fixed       latency-sensitive AI demand                       [MW]
%     flex_base   baseline placement of the delay-tolerant bundles  [MW]
%     load_base   fixed + flex_base                                 [MW]
%     solar,wind  on-site renewable generation                      [MW]
%     ren         solar + wind                                      [MW]
%     ci          grid carbon intensity                        [kgCO2/MWh]
%     cap_nonfirm time-varying non-firm connection envelope         [MW]
%     cap_phased  phased connection envelope                        [MW]

f = fullfile(cfg.paths.data, cfg.benchmark_csv);
if exist(f, 'file') == 2
    R = qh2dc_readcsv(f);
else
    warning('qh2dc:benchmarkMissing', ...
        'Benchmark CSV not found at %s - regenerating from the seeded generator.', f);
    R = qh2dc_build_benchmark(cfg);
end

B.hour        = R.hour_index(:);
B.day         = R.day(:);
B.hod         = R.hour_of_day(:);
B.fixed       = R.fixed_ai_load_MW(:);
B.flex_base   = R.baseline_flexible_load_MW(:);
B.load_base   = R.total_baseline_load_MW(:);
B.solar       = R.solar_MW(:);
B.wind        = R.wind_MW(:);
B.ren         = R.renewable_MW(:);
B.ci          = R.grid_carbon_kgCO2_per_MWh(:);
B.cap_nonfirm = R.nonfirm_connection_cap_MW(:);
B.cap_phased  = R.phased_connection_cap_MW(:);
B.T           = numel(B.hour);

% ---- validation gate of the data-engineering layer --------------------
assert(B.T == cfg.T, 'Benchmark horizon (%d) differs from cfg.T (%d).', B.T, cfg.T);
assert(all(isfinite([B.fixed; B.ren; B.ci])), 'Non-finite values in the benchmark.');
assert(all(B.fixed > 0), 'Fixed AI demand must be strictly positive.');
assert(max(abs(B.load_base - (B.fixed + B.flex_base))) < 1e-9, ...
       'Baseline load column is inconsistent with its components.');
assert(max(abs(B.ren - (B.solar + B.wind))) < 1e-9, ...
       'Renewable column is inconsistent with solar and wind.');
end
