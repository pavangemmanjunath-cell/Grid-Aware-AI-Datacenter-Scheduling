function B = qh2dc_ingest_trace(cfg, traceFile, renFile, ciFile)
%QH2DC_INGEST_TRACE  Production-trace path of the data-engineering layer.
%
%   This is the function to point at real open data instead of the shipped
%   benchmark.  It performs the five steps described in Section 3 of the
%   paper: validate, classify, map to power, aggregate to hourly resolution
%   and join with the energy-side series.
%
%   traceFile  GPU cluster trace CSV.  Expected columns (rename to match):
%              start_time, end_time, gpu_num, gpu_util, job_type, priority
%              Source: https://github.com/alibaba/clusterdata
%   renFile    hourly renewable generation CSV with columns hour, solar_MW,
%              wind_MW.  Sources: https://www.renewables.ninja/ or
%              https://open-power-system-data.org/
%   ciFile     hourly grid carbon intensity CSV with columns hour,
%              ci_kg_per_MWh.  Source: https://carbonintensity.org.uk/
%
%   The classification rule below is the one used in the paper: interactive
%   and high-priority serving jobs are fixed; training, fine-tuning, offline
%   inference and data-engineering jobs are delay tolerant.  Calibrate
%   cfg.power against measured facility data before quoting absolute MW -
%   see https://ieee-dataport.org/open-access/data-server-energy-consumption-dataset

Tr = qh2dc_readcsv(traceFile);

% ---- 1. validate --------------------------------------------------------
keep = isfinite(Tr.start_time) & isfinite(Tr.end_time) & ...
       Tr.end_time > Tr.start_time & Tr.gpu_num > 0;
fn = fieldnames(Tr);
for i = 1:numel(fn), Tr.(fn{i}) = Tr.(fn{i})(keep); end

% ---- 2. classify --------------------------------------------------------
% job_type encoding in the caller's dictionary: 1 = online inference,
% 2 = training, 3 = fine-tuning, 4 = offline inference, 5 = data pipeline.
isFixed = (Tr.job_type == 1) | (Tr.priority >= 9);

% ---- 3. map utilisation to electrical power ----------------------------
p = cfg.power;
u = min(1, max(0, Tr.gpu_util));
Pjob = (Tr.gpu_num / 1000) .* (p.P_idle_gpu + (p.P_rated_gpu - p.P_idle_gpu) .* u);
Pjob = Pjob * p.overhead_IT * p.PUE;      % IT overhead and facility overhead

% ---- 4. aggregate to hourly profiles -----------------------------------
h0 = min(Tr.start_time);
sh = floor((Tr.start_time - h0) / 3600) + 1;
eh = ceil((Tr.end_time  - h0) / 3600);
T  = cfg.T;
fixed = zeros(T, 1); flex = zeros(T, 1);
for i = 1:numel(Pjob)
    a = max(1, sh(i)); b = min(T, eh(i));
    if b < a, continue; end
    if isFixed(i), fixed(a:b) = fixed(a:b) + Pjob(i);
    else,          flex(a:b)  = flex(a:b)  + Pjob(i);
    end
end

% ---- 5. join with the energy-side series -------------------------------
Rn = qh2dc_readcsv(renFile);
Ci = qh2dc_readcsv(ciFile);
hour = (0:T-1).';
hod  = mod(hour, 24);

B.hour = hour; B.day = floor(hour/24); B.hod = hod; B.T = T;
B.fixed = fixed; B.flex_base = flex; B.load_base = fixed + flex;
B.solar = Rn.solar_MW(1:T); B.wind = Rn.wind_MW(1:T);
B.ren = B.solar + B.wind;
B.ci  = Ci.ci_kg_per_MWh(1:T);

cap = repmat(cfg.nonfirm_normal, T, 1);
inwin = hod >= cfg.nonfirm_window(1) & hod <= cfg.nonfirm_window(2);
cap(inwin) = cfg.nonfirm_reduced;
B.cap_nonfirm = cap;
stage = min(numel(cfg.phased_levels), floor(hour / cfg.phased_stage_h) + 1);
B.cap_phased = cfg.phased_levels(stage).';
end
