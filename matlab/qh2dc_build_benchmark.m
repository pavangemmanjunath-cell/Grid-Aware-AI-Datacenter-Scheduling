function R = qh2dc_build_benchmark(cfg)
%QH2DC_BUILD_BENCHMARK  Deterministic generator of the 168-h benchmark.
%
%   The shipped CSV was produced by this generator and is the artefact used
%   for the published numbers.  The generator is provided so that the study
%   can be re-run at other horizons, other renewable shares or other
%   envelopes, and so that the structure of the benchmark is inspectable
%   rather than opaque.  It is a simulation benchmark: it is not raw
%   operator data and is not presented as such.

T = cfg.T;
rand('seed', cfg.rng_seed);   %#ok<RAND>
randn('seed', cfg.rng_seed);  %#ok<RAND>

hour = (0:T-1).';
day  = floor(hour / 24);
hod  = mod(hour, 24);

% ---- fixed, latency-sensitive AI demand --------------------------------
% Inference-dominated: a shallow daily shape on a high base, plus noise.
base  = 7.15;
shape = 0.55 * sin(2*pi*(hod - 3)/24) + 0.20 * sin(4*pi*hod/24);
fixed = base + shape + 0.18 * randn(T, 1);

% ---- delay-tolerant AI bundles -----------------------------------------
flex = zeros(T, 1);
isflex = ismember(hod, cfg.flex_hours);
flex(isflex) = 5.2 + 2.8 * rand(sum(isflex), 1);

% ---- on-site renewables -------------------------------------------------
solar_shape = max(0, sin(pi * (hod - 6) / 12));
clear_sky   = 8.6 * solar_shape.^1.35;
cloud       = 0.70 + 0.30 * rand(T, 1);
solar       = clear_sky .* cloud;
solar(hod < 7 | hod > 18) = 0;

wind = zeros(T, 1);
w = 3.0;
for t = 1:T                     % first-order autoregressive wind process
    w = 0.88 * w + 0.12 * (2.6 + 2.2 * rand()) + 0.35 * randn();
    wind(t) = max(0.3, min(5.0, w));
end
ren = solar + wind;

% ---- grid carbon intensity ---------------------------------------------
% Anti-correlated with the solar shape, as in a solar-rich bidding zone.
ci = 470 - 160 * (solar ./ max(solar)) - 22 * (wind - mean(wind));
ci = max(180, ci + 14 * randn(T, 1));

% ---- connection envelopes ----------------------------------------------
cap_nf = repmat(cfg.nonfirm_normal, T, 1);
inwin  = hod >= cfg.nonfirm_window(1) & hod <= cfg.nonfirm_window(2);
cap_nf(inwin) = cfg.nonfirm_reduced;

cap_ph = zeros(T, 1);
stage  = min(numel(cfg.phased_levels), floor(hour / cfg.phased_stage_h) + 1);
for t = 1:T, cap_ph(t) = cfg.phased_levels(stage(t)); end

R.hour_index                 = hour;
R.day                        = day;
R.hour_of_day                = hod;
R.fixed_ai_load_MW           = fixed;
R.baseline_flexible_load_MW  = flex;
R.total_baseline_load_MW     = fixed + flex;
R.solar_MW                   = solar;
R.wind_MW                    = wind;
R.renewable_MW               = ren;
R.grid_carbon_kgCO2_per_MWh  = ci;
R.nonfirm_connection_cap_MW  = cap_nf;
R.phased_connection_cap_MW   = cap_ph;
R.nonfirm_constraint_event   = double(inwin);
end
