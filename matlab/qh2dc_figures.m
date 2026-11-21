function qh2dc_figures(cfg, B, J, S, Ms, lbl, Qs, BF, QA)
%QH2DC_FIGURES  Render the six publication figures.
%
%   Elsevier artwork naming is used: gr<N> for figures.  Each file is written
%   twice, as PDF for the LaTeX build and as 300 dpi PNG for the Word route.
%
%     gr1  Framework and data flow                      (Fig. 1)
%     gr2  The 168-h benchmark                           (Fig. 2)
%     gr3  QAOA landscape and output distribution        (Fig. 3)
%     gr4  Required connection capacity, six scenarios   (Fig. 4)
%     gr5  Non-firm operation over the first 48 h        (Fig. 5)
%     gr6  Green-hydrogen buffering and inventory        (Fig. 6)
%
%   The file number matches the figure number in the manuscript, as the
%   Elsevier artwork-naming rule requires.

od = cfg.paths.figures;
col = struct('grid', [.29 .29 .29], 'ren', [.17 .50 .72], 'solar', [.88 .52 .08], ...
             'wind', [.30 .57 .13], 'h2', [.50 .45 .67], 'fc', [.77 .11 .49], ...
             'cap', [.84 .10 .11], 'grey', [.80 .80 .80]);
t  = B.hour;
T  = B.T;

% ================================================================= gr1 ==
% Architecture figure.  The layout deliberately separates two things that the
% previous version drew as peers:
%
%   (a) the CLASSICAL pipeline, which is what actually produces R0-R5.  The
%       MILP selects the binary workload placement AND the continuous energy
%       variables, and the capacity bisection re-solves it.  This is a closed
%       operational loop.
%   (b) the QUANTUM branch, which is offline methodological validation.  The
%       QUBO is built from the same analytical table, solved twice (exhaustive
%       reference and QAOA) and compared.  Its output is NEVER fed back into
%       the dispatch - see main_qh2dc.m, where the QAOA block runs after the
%       scenarios are already complete.
%
% Drawing them as parallel inputs to a shared feasibility check, as the
% previous version did, implied that the quantum routine controlled the
% electrolyser and fuel cell.  It does not.
%
% Style: full text width, short noun-phrase labels, headings in bold, a dashed
% enclosure and dashed arrows for the offline branch so the distinction also
% survives greyscale printing.

f = figure('Color', 'w', 'Units', 'inches', 'Position', [1 1 6.5 4.0]);
ax = axes('Position', [0.005 0.005 0.99 0.99]); axis(ax, [0 100 0 64]); axis off; hold on;

% One axis unit = 6.5 in / 100 = 0.065 in = 4.68 pt.  A 17-unit box is ~80 pt,
% which holds ~18 characters at 8 pt bold or ~20 at 7.5 pt roman.  Labels are
% kept inside that budget so nothing overflows its box at final print size.
% 7.5 pt is above the Elsevier 7 pt artwork minimum; the figure is placed at
% width = \hsize, so it is reproduced 1:1 and the point sizes are as drawn.

cIn  = [0.20 0.42 0.62];
cDE  = [0.42 0.35 0.60];
cCL  = [0.20 0.48 0.18];
cOut = [0.32 0.32 0.32];
cQ   = [0.62 0.12 0.42];

% ---- offline branch enclosure (drawn first) -----------------------------
rectangle('Position', [1.0 1.0 98.0 24.0], 'Curvature', 0.03, ...
          'EdgeColor', [0.58 0.58 0.58], 'LineStyle', '--', 'LineWidth', 0.9);
text(24.0, 22.3, 'OFFLINE QUANTUM PLACEMENT VALIDATION', ...
     'HorizontalAlignment', 'left', 'FontSize', 7.5, 'FontWeight', 'bold', ...
     'Color', [0.40 0.40 0.40]);
text(24.0, 19.3, 'validates the placement decomposition only \rightarrow does not control the physical dispatch', ...
     'HorizontalAlignment', 'left', 'FontSize', 7, 'FontAngle', 'italic', ...
     'Color', [0.48 0.48 0.48]);

% ---- inputs --------------------------------------------------------------
local_node( 1.0, 51.0, 17.0, 11.0, 'Workload Trace', ...
           {'class, priority,', 'utilisation'}, cIn, '-');
local_node( 1.0, 40.5, 17.0, 10.0, 'Renewable & Grid', ...
           {'solar, wind,', 'carbon intensity'}, cIn, '-');
local_node( 1.0, 30.0, 17.0, 10.0, 'Grid Envelope', ...
           {'firm, non-firm,', 'phased'}, cIn, '-');

% ---- data engineering ----------------------------------------------------
local_node(21.5, 31.0, 16.0, 30.0, 'Data Engineering', ...
           {'validate & align', 'classify LS / DT', 'map to power', 'hourly join'}, ...
           cDE, '-');

% ---- shared analytical table --------------------------------------------
local_node(41.0, 36.0, 16.0, 20.0, '168-h Benchmark', ...
           {'load, renewables', 'CI, envelope', 'DT candidates'}, cDE, '-');

% ---- classical scheduler -------------------------------------------------
local_node(60.5, 31.0, 17.0, 30.0, 'MILP Scheduler', ...
           {'DT placement', 'grid import', 'electrolyser, H_2', 'fuel cell, curtail'}, ...
           cCL, '-');

% ---- feasibility and metrics --------------------------------------------
local_node(81.0, 44.0, 17.0, 13.0, 'Feasibility & SLA', ...
           {'envelope check', 'zero unserved'}, cCL, '-');
local_node(81.0, 31.0, 17.0, 11.0, 'Metrics', ...
           {'MW, MWh, tCO_2', 'delay, shifted %'}, cOut, '-');

% ---- offline quantum branch ---------------------------------------------
local_node( 3.0, 3.5, 17.0, 13.0, 'Daily DT Subset', ...
           {'4 bundles', '3 slots each'}, cQ, '--');
local_node(24.5, 3.5, 17.0, 13.0, 'QUBO Builder', ...
           {'12 variables', '4096 states'}, cQ, '--');
local_node(46.0, 10.3, 17.0, 6.2, 'Exhaustive', {}, cQ, '--');
local_node(46.0, 3.5, 17.0, 6.2, 'QAOA  p = 1, 2', {}, cQ, '--');
local_node(67.5, 3.5, 17.0, 13.0, 'Agreement Check', ...
           {'mode = optimum', 'gap = 0'}, cQ, '--');

% ---- classical arrows ----------------------------------------------------
local_arr(18.2, 56.5, 21.3, 51.0, '-');
local_arr(18.2, 45.5, 21.3, 46.0, '-');
local_arr(18.2, 35.0, 21.3, 41.0, '-');
local_arr(37.7, 46.0, 40.8, 46.0, '-');
local_arr(57.2, 46.0, 60.3, 46.0, '-');
local_arr(77.7, 49.0, 80.8, 50.5, '-');
local_arr(89.5, 43.8, 89.5, 42.2, '-');

% capacity-bisection feedback into the MILP
local_dash(98.2, 50.5, 99.3, 50.5);
local_dash(99.3, 50.5, 99.3, 62.6);
local_dash(99.3, 62.6, 69.0, 62.6);
local_darr(69.0, 62.6, 69.0, 61.2);
text(84.0, 63.4, 'capacity bisection: re-solve if infeasible', ...
     'HorizontalAlignment', 'center', 'FontSize', 7, 'Color', [0.40 0.40 0.40]);

% ---- the shared table also seeds the offline branch ---------------------
local_dash(49.0, 35.8, 49.0, 28.0);
local_dash(49.0, 28.0, 11.5, 28.0);
local_darr(11.5, 28.0, 11.5, 16.7);
text(31.0, 29.4, 'same analytical table', 'HorizontalAlignment', 'center', ...
     'FontSize', 7, 'Color', [0.48 0.48 0.48]);

% ---- quantum arrows ------------------------------------------------------
local_arr(20.2, 10.0, 24.3, 10.0, '--');
local_arr(41.7, 11.3, 45.8, 12.6, '--');
local_arr(41.7,  8.7, 45.8,  6.6, '--');
local_arr(63.2, 12.6, 67.3, 11.3, '--');
local_arr(63.2,  6.6, 67.3,  8.7, '--');

local_save(f, fullfile(od, 'gr1'), false);

% ================================================================= gr2 ==
f = figure('Color', 'w', 'Units', 'inches', 'Position', [1 1 6.5 4.25]);
subplot(3,1,1); hold on; box on;
bar(t, B.flex_base, 0.85, 'FaceColor', col.grey, 'EdgeColor', 'none');
plot(t, B.fixed, 'Color', [0 0 0], 'LineWidth', 0.9);
plot(t, B.ren, 'Color', col.ren, 'LineWidth', 0.9);
ylabel('Power (MW)'); ylim([0 17]); xlim([0 T-1]);
legend({'Baseline flexible bundles', 'Fixed AI demand', 'Renewable supply'}, ...
       'Location', 'northwest', 'Orientation', 'horizontal'); legend boxoff;
subplot(3,1,2); hold on; box on;
area(t, [B.solar B.wind], 'LineStyle', 'none');
colormap(gca, [col.solar; col.wind]);
ylabel('Power (MW)'); xlim([0 T-1]);
legend({'Solar', 'Wind'}, 'Location', 'northeast', 'Orientation', 'horizontal'); legend boxoff;
ax3 = subplot(3,1,3); hold on; box on;
stairs(t, B.cap_nonfirm, 'Color', col.cap, 'LineWidth', 0.9);
stairs(t, B.cap_phased, '--', 'Color', [.22 .49 .72], 'LineWidth', 0.9);
ylabel('Cap (MW)'); xlabel('Hour of the 168 h benchmark'); xlim([0 T-1]);
legend({'Non-firm envelope', 'Phased envelope'}, 'Location', 'southeast', ...
       'Orientation', 'horizontal'); legend boxoff;
% grid carbon intensity on a right-hand axis, as stated in the Fig. 2 caption.
% A transparent overlay axes is used instead of YYAXIS so that the figure also
% renders under GNU Octave.
pos = get(ax3, 'Position');
ax3b = axes('Position', pos, 'Color', 'none', 'YAxisLocation', 'right', ...
            'XAxisLocation', 'top', 'XTick', [], 'XColor', 'none', ...
            'YColor', [.47 .47 .47], 'Box', 'off');
hold(ax3b, 'on');
plot(ax3b, t, B.ci, 'Color', [.47 .47 .47], 'LineWidth', 0.6);
set(ax3b, 'XLim', [0 T-1]);
ylabel(ax3b, {'Carbon int.', '(kg/MWh)'}, 'Color', [.47 .47 .47]);
local_save(f, fullfile(od, 'gr2'));

% ================================================================= gr4 ==
f = figure('Color', 'w', 'Units', 'inches', 'Position', [1 1 6.5 2.75]);
caps = cellfun(@(m) m.conn_MW, Ms);
cmap = [.55 .55 .55; col.ren; col.h2; col.wind; col.fc; col.solar];
hold on; box on;
for i = 1:numel(caps)
    bar(i, caps(i), 0.62, 'FaceColor', cmap(i,:), 'EdgeColor', 'k', 'LineWidth', 0.4);
    text(i, caps(i) + 0.3, sprintf('%.2f MW', caps(i)), ...
         'HorizontalAlignment', 'center', 'FontSize', 8);
    if i > 1
        text(i, caps(i)/2, sprintf('-%.1f%%', 100*(1 - caps(i)/caps(1))), ...
             'HorizontalAlignment', 'center', 'FontSize', 8, 'Color', 'w', ...
             'FontWeight', 'bold');
    end
end
plot([0.4 numel(caps)+0.6], [caps(1) caps(1)], ':', 'Color', [.55 .55 .55]);
set(gca, 'XTick', 1:numel(caps), 'XTickLabel', ...
    {'R0', 'R1', 'R2', 'R3', 'R4', 'R5'});
ylabel({'Required connection', 'capacity (MW)'}); ylim([0 17.5]);
xlim([0.4 numel(caps)+0.6]);
local_save(f, fullfile(od, 'gr4'));

% ================================================================= gr5 ==
H = 48; hh = (0:H-1).';
f = figure('Color', 'w', 'Units', 'inches', 'Position', [1 1 6.5 4.5]);
subplot(3,1,1); hold on; box on;
% S2u is the unconstrained hydrogen-only dispatch replayed against the
% envelope, not a solution that was optimised against it.
within = min(S.S2u.pg(1:H), B.cap_nonfirm(1:H));
exc    = max(0, S.S2u.pg(1:H) - B.cap_nonfirm(1:H));
hb = bar(hh, [within exc], 0.8, 'stacked', 'EdgeColor', 'none');
set(hb(1), 'FaceColor', [.79 .79 .79]); set(hb(2), 'FaceColor', col.cap);
stairs(hh, B.cap_nonfirm(1:H), 'Color', col.cap, 'LineWidth', 1.1);
ylabel('Grid import (MW)'); ylim([0 13.5]); xlim([-0.6 H-0.4]);
legend({'Unconstrained H_2-only dispatch, replayed', 'Envelope exceedance', ...
        'Non-firm envelope C_t'}, 'Location', 'northwest', ...
        'Orientation', 'horizontal'); legend boxoff;
subplot(3,1,2); hold on; box on;
bar(hh, S.S4.pg(1:H), 0.8, 'FaceColor', col.grid, 'EdgeColor', 'none');
stairs(hh, B.cap_nonfirm(1:H), 'Color', col.cap, 'LineWidth', 1.1);
ylabel('Grid import (MW)'); ylim([0 13.5]); xlim([-0.6 H-0.4]);
legend({'Optimised grid import', 'Non-firm envelope C_t'}, ...
       'Location', 'northwest', 'Orientation', 'horizontal'); legend boxoff;
subplot(3,1,3); hold on; box on;
bar(hh, B.flex_base(1:H), 0.8, 'FaceColor', [.79 .79 .79], 'EdgeColor', [.6 .6 .6]);
bar(hh, S.S4.sched(1:H), 0.42, 'FaceColor', col.wind, 'EdgeColor', 'none');
ylabel({'Flexible', 'bundle (MW)'}); xlabel('Hour of the 168 h benchmark (first 48 h shown)');
ylim([0 15]); xlim([-0.6 H-0.4]);
legend({'Baseline slot', 'Selected slot'}, 'Location', 'north', ...
       'Orientation', 'horizontal'); legend boxoff;
local_save(f, fullfile(od, 'gr5'));

% ================================================================= gr6 ==
f = figure('Color', 'w', 'Units', 'inches', 'Position', [1 1 6.5 3.2]);
subplot(2,1,1); hold on; box on;
bar(t, S.S1.pc, 1.0, 'FaceColor', [.85 .85 .85], 'EdgeColor', 'none');
bar(t, S.S2.pe, 0.55, 'FaceColor', col.h2, 'EdgeColor', 'none');
bar(t, -S.S2.pf, 0.55, 'FaceColor', col.fc, 'EdgeColor', 'none');
plot([0 T-1], [0 0], 'k', 'LineWidth', 0.5);
ylabel('Power (MW)'); xlim([0 T-1]);
legend({'Renewable surplus without H_2', 'Electrolyser intake', 'Fuel-cell output'}, ...
       'Location', 'northwest', 'Orientation', 'horizontal'); legend boxoff;
subplot(2,1,2); hold on; box on;
plot(t, S.S2.h, 'Color', col.h2, 'LineWidth', 1.0);
plot([0 T-1], [cfg.H_max cfg.H_max], '--', 'Color', col.cap, 'LineWidth', 0.7);
plot([0 T-1], [cfg.H_init cfg.H_init], ':', 'Color', [.53 .53 .53], 'LineWidth', 0.7);
ylabel({'H_2 stored', '(MWh_{H2})'}); xlabel('Hour of the 168 h benchmark');
ylim([0 23.5]); xlim([0 T-1]);
legend({'H_2 inventory', 'Storage limit'}, 'Location', 'northeast', ...
       'Orientation', 'horizontal'); legend boxoff;
local_save(f, fullfile(od, 'gr6'));

% ================================================================= gr3 ==
% The cost operator is a rescaled real diagonal, so the expected cost is not
% pi-periodic in gamma.  Draw the landscape over the range that contains the
% optimised angles rather than folding it into [0, pi].
% The window must contain the optimised angles.  fminsearch can return an
% angle equivalent to, but numerically far from, the one that produced the
% shipped figure (the cost is periodic in beta), and a hard-coded window then
% leaves the marker floating outside the drawn landscape.  Centre the window
% on the solution instead, keeping at least the original span.
ng = 41;
g_opt = QA.params(1); b_opt = QA.params(2);
gv = linspace(min(0, g_opt - 1), max(12, g_opt + 1), ng);
bv = linspace(b_opt - 1.5, b_opt + 1.5, ng);
Lz = zeros(ng, ng);
cs = BF.cost / max(abs(BF.cost));
for i = 1:ng
    for k = 1:ng
        psi = local_qaoa_state([gv(i); bv(k)], 1, cs, Qs.n);
        Lz(k, i) = real(sum(abs(psi).^2 .* BF.cost));
    end
end
f = figure('Color', 'w', 'Units', 'inches', 'Position', [1 1 6.5 2.6]);
subplot(1,2,1);
contourf(gv, bv, Lz, 22, 'LineStyle', 'none'); hold on; box on;
plot(QA.params(1), QA.params(2), 'wp', ...
     'MarkerSize', 9, 'MarkerFaceColor', 'w', 'MarkerEdgeColor', 'k');
xlabel('\gamma'); ylabel('\beta'); title('(a) p = 1 energy landscape', 'FontWeight', 'normal');
c = colorbar; ylabel(c, 'Expected QUBO cost');
subplot(1,2,2);
[~, ord] = sort(BF.cost); fl = BF.feasible(ord); pr = QA.prob(ord) * 100;
idx = (1:BF.n_states).';
semilogy(idx(~fl), max(pr(~fl), 1e-9), '.', 'Color', [.82 .82 .82], 'MarkerSize', 3); hold on; box on;
semilogy(idx(fl), max(pr(fl), 1e-9), '.', 'Color', col.fc, 'MarkerSize', 8);
xlabel('Basis states ordered by QUBO cost'); ylabel('Measurement probability (%)');
title('(b) output distribution at the optimised angles', 'FontWeight', 'normal');
legend({sprintf('Infeasible states (%d)', BF.n_states - BF.n_feasible), ...
        sprintf('Feasible one-hot states (%d)', BF.n_feasible)}, ...
        'Location', 'southwest'); legend boxoff;
xlim([0 BF.n_states]); ylim([1e-7 2]);
local_save(f, fullfile(od, 'gr3'));
end

% ======================================================================== %
function local_node(x, y, w, h, head, body, c, ls)
%LOCAL_NODE  Rounded box with a bold heading and short body lines.
rectangle('Position', [x y w h], 'Curvature', 0.10, 'EdgeColor', c, ...
          'FaceColor', min(1, c * 0.16 + 0.90), 'LineWidth', 0.9, 'LineStyle', ls);
n = numel(body);
if n == 0
    text(x + w/2, y + h/2, head, 'HorizontalAlignment', 'center', ...
         'VerticalAlignment', 'middle', 'FontSize', 8, 'FontWeight', 'bold');
    return;
end
lead = 3.0;
top  = y + h - (h - (n + 0.6) * 3.0) / 2 - 2.2;
text(x + w/2, top, head, 'HorizontalAlignment', 'center', ...
     'VerticalAlignment', 'middle', 'FontSize', 8, 'FontWeight', 'bold');
for i = 1:n
    if isempty(body{i}), continue; end
    text(x + w/2, top - i*lead, body{i}, 'HorizontalAlignment', 'center', ...
         'VerticalAlignment', 'middle', 'FontSize', 7.5);
end
end

function local_arr(x1, y1, x2, y2, ls)
plot([x1 x2], [y1 y2], ls, 'Color', [.32 .32 .32], 'LineWidth', 1.0);
local_head(x1, y1, x2, y2);
end

function local_dash(x1, y1, x2, y2)
plot([x1 x2], [y1 y2], '--', 'Color', [.45 .45 .45], 'LineWidth', 0.9);
end

function local_darr(x1, y1, x2, y2)
local_dash(x1, y1, x2, y2);
local_head(x1, y1, x2, y2);
end

function local_head(x1, y1, x2, y2)
d = [x2-x1, y2-y1]; L = max(norm(d), eps); u = d / L;
n = [-u(2), u(1)];
a = 1.9; b = 0.95;                       % length and half-width of the head
tip = [x2, y2];
p1 = tip - a*u + b*n;
p2 = tip - a*u - b*n;
patch([tip(1) p1(1) p2(1)], [tip(2) p1(2) p2(2)], [.32 .32 .32], ...
      'EdgeColor', 'none');
end

function local_box(x, y, w, h, s, c)
rectangle('Position', [x y w h], 'Curvature', 0.15, 'EdgeColor', c, ...
          'FaceColor', min(1, c + 0.78), 'LineWidth', 0.8);
text(x + w/2, y + h/2, s, 'HorizontalAlignment', 'center', ...
     'VerticalAlignment', 'middle', 'FontSize', 7);
end

function local_arrow(x1, y1, x2, y2)
plot([x1 x2], [y1 y2], '-', 'Color', [.35 .35 .35], 'LineWidth', 0.7);
d = [x2-x1, y2-y1]; d = d / max(norm(d), eps) * 0.12;
plot(x2 - d(1), y2 - d(2), '>', 'Color', [.35 .35 .35], 'MarkerSize', 3, ...
     'MarkerFaceColor', [.35 .35 .35]);
end

function local_dashed(x1, y1, x2, y2)
plot([x1 x2], [y1 y2], '--', 'Color', [.35 .35 .35], 'LineWidth', 0.7);
end

function local_dashed_arrow(x1, y1, x2, y2)
local_dashed(x1, y1, x2, y2);
d = [x2-x1, y2-y1]; d = d / max(norm(d), eps) * 0.12;
plot(x2 - d(1), y2 - d(2), '^', 'Color', [.35 .35 .35], 'MarkerSize', 3, ...
     'MarkerFaceColor', [.35 .35 .35]);
end

function local_save(f, base, unify)
%LOCAL_SAVE  Export at 300 dpi.  UNIFY (default true) forces every font to 8 pt,
%   which is right for the plots but would flatten the deliberate heading /
%   body hierarchy of the architecture figure, so gr1 passes false.
if nargin < 3, unify = true; end
set(findall(f, '-property', 'FontName'), 'FontName', 'Times');
if unify
    set(findall(f, '-property', 'FontSize'), 'FontSize', 8);
end
try
    print(f, [base '.pdf'], '-dpdf', '-bestfit', '-r300');
catch
    print(f, [base '.pdf'], '-dpdf', '-r300');
end
print(f, [base '.png'], '-dpng', '-r300');
close(f);
end

function psi = local_qaoa_state(x, p, cs, n)
Nst = 2^n; psi = ones(Nst, 1) / sqrt(Nst);
g = x(1:p); b = x(p+1:2*p);
for i = 1:p
    psi = psi .* exp(-1i * g(i) * cs);
    c = cos(b(i)); s = -1i * sin(b(i));
    for qb = 0:(n-1)
        m = bitshift(1, qb);
        i0 = find(bitand((0:Nst-1).', m) == 0);
        i1 = i0 + m;
        a0 = psi(i0); a1 = psi(i1);
        psi(i0) = c * a0 + s * a1;
        psi(i1) = s * a0 + c * a1;
    end
end
end
