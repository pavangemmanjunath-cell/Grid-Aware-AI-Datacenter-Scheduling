function qh2dc_assert_feasible(S, name)
%QH2DC_ASSERT_FEASIBLE  Stop with a readable message on an infeasible scenario.
%
%   QH2DC_DISPATCH returns [] when an instance admits no schedule with zero
%   unserved energy.  Passing that [] straight into QH2DC_METRICS produces an
%   opaque "Dot indexing is not supported" error, which hides the real cause.
%   This gate turns it into a statement of what actually happened and of what
%   the two usual remedies are.

if ~isempty(S), return; end

if exist('intlinprog', 'file') == 2 || exist('intlinprog', 'builtin') == 5
    hint = ['The MILP solver found no feasible schedule.  Check the envelope ' ...
            'and the hydrogen ratings in qh2dc_config.'];
else
    hint = ['No MILP solver is installed, so the toolbox-free local search in ' ...
            'qh2dc_fallback_dispatch was used.  That path is a heuristic and ' ...
            'can miss a placement the MILP would find.  Install the ' ...
            'Optimization Toolbox (intlinprog) or run under GNU Octave (glpk) ' ...
            'to reproduce the published figures.'];
end

error('qh2dc:infeasible', ...
      ['Scenario %s has no feasible schedule with zero unserved energy.\n' ...
       '%s'], name, hint);
end
