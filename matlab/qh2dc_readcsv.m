function S = qh2dc_readcsv(f)
%QH2DC_READCSV  Minimal numeric CSV reader with a header row.
%   Works on base MATLAB and on GNU Octave; no toolbox required.

fid = fopen(f, 'r');
if fid < 0, error('qh2dc:openFailed', 'Cannot open %s', f); end
hdr = strtrim(fgetl(fid));
names = strsplit(hdr, ',');
data = [];
while true
    ln = fgetl(fid);
    if ~ischar(ln), break; end
    ln = strtrim(ln);
    if isempty(ln), continue; end
    v = str2double(strsplit(ln, ','));
    data(end+1, :) = v; %#ok<AGROW>
end
fclose(fid);
S = struct();
for k = 1:numel(names)
    nm = strtrim(names{k});
    nm(~(isstrprop(nm, 'alphanum') | nm == '_')) = '_';
    if ~isstrprop(nm(1), 'alpha'), nm = ['v_' nm]; end
    S.(nm) = data(:, k);
end
end
