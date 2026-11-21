# Related work, patents and public software (survey, 2026-11-21)

A dated survey of the closest papers, patents and public repositories. Every entry was checked against its
primary source (arXiv abstract page, Google Patents, GitHub REST API, Crossref) on **2026-11-21**. Star
counts are a snapshot. This is a literature and software survey — **not a novelty claim and not a legal
or patentability opinion**.

Key: ✓ stated in the source · ✗ absent · – not stated · P partly.

## Closest research papers

| Work | AI / DC load | H₂ chain (electrolyser + tank + fuel cell) | Solar / wind | Minimises grid connection | Non-firm / phased limit | Job time-shifting | QUBO / QAOA | Public code |
|---|---|---|---|---|---|---|---|---|
| **This repository** (ICMLDE 2026, paper 1939) | ✓ | ✓ | ✓ / ✓ | ✓ (bisection on capacity) | ✓ / ✓ | ✓ | ✓ (verified by enumeration) | ✓ |
| Butt, Fatima & Li, *Minimizing Grid Interconnection Capacity Requirements for AI Data Centers: A Developer-Side Planning Framework with Onsite Resources and Workload Flexibility*, [arXiv:2608.29359](https://arxiv.org/abs/2608.29359) (Aug 2026) | ✓ | ✗ | ✓ / ✗ | ✓ | – | ✓ (deadline-constrained deferral) | ✗ | none listed |
| Fatima & Li, *Unlocking AI Data Center Interconnection Capacity Through Coordinated Grid and Data Center Flexibility*, [arXiv:2610.05502](https://arxiv.org/abs/2610.05502) (Oct 2026) | ✓ | ✗ | ✗ | maximises hosting capacity (grid-side OPF) | P | ✓ | ✗ | none listed |
| Li, Tong & Mount, *Energy Management for Renewable-Colocated Artificial Intelligence Data Centers*, [arXiv:2507.08011](https://arxiv.org/abs/2507.08011) (2025) | ✓ | ✗ | wind only | ✗ (cost / market) | – | ✓ | ✗ | none |
| Riepin, Brown & Zavala, *Spatio-temporal load shifting for truly clean computing*, Adv. Appl. Energy 17 (2025), [doi:10.1016/j.adapen.2024.100202](https://doi.org/10.1016/j.adapen.2024.100202) | ✓ | – | ✓ | ✗ (24/7 CFE cost) | ✗ | ✓ (space + time) | ✗ | ✓ [Irieo/space-time-optimization](https://github.com/Irieo/space-time-optimization) |
| Wiesner et al., *Let's Wait Awhile*, Middleware 2021, [doi:10.1145/3464298.3493399](https://doi.org/10.1145/3464298.3493399) | ✓ | ✗ | ✗ | ✗ (carbon) | ✗ | ✓ | ✗ | ✓ [dos-group/lets-wait-awhile](https://github.com/dos-group/lets-wait-awhile) |
| Radovanović et al., *Carbon-Aware Computing for Datacenters*, IEEE TPWRS (2023), [doi:10.1109/TPWRS.2022.3173250](https://doi.org/10.1109/TPWRS.2022.3173250) | ✓ | ✗ | ✗ | ✗ (carbon) | ✗ | ✓ | ✗ | not public |

The closest formulation is arXiv:2608.29359, which also minimises the interconnection capacity of an AI
data centre with on-site resources and workload flexibility. The differences, as stated in the sources:
it co-sizes PV and other on-site assets under an investment budget; this work dispatches a fixed
solar + wind + electrolyser–tank–fuel-cell plant, evaluates firm, phased and non-firm envelopes, and adds
a QUBO/QAOA layer for the placement block. The two were developed independently; this repository makes no
claim of priority.

## Patents (descriptive only)

| Patent | Assignee | Content relevant here (from abstract / claims) | Difference from this work |
|---|---|---|---|
| [US 2026/0051756 A1](https://patents.google.com/patent/US20260051756A1/en) "Power systems for data centers" (Lovato, Kunthia, Mathur; published 2026-02-19) | Data Volt Information Technology Co. | Routes surplus PV/wind power to hydrogen production or other on-site equipment by fixed rules; a hydrogen generator covers shortfalls | Power routing rules; no optimisation, no compute-job scheduling, no grid-connection limit, no quantum method |
| [US 12,469,861 B2](https://patents.google.com/patent/US12469861B2/en) "Data center balance of plant integrated into fuel cell system design" (granted 2025-11-11) | Google LLC | PEM fuel cells supplied from an on-site liquid-hydrogen supply, heat recovery | No electrolyser, no scheduling, no connection limit |
| [US 2024/0288122 A1](https://patents.google.com/patent/US20240288122A1/en) "Hydrogen fueling and storage optimization model" (published 2024-08-29) | Google LLC | Sizing the liquid-hydrogen supply and refuelling for backup fuel cells | Fuel logistics; no renewables, electrolyser or job scheduling |
| [US 12,438,380 B2](https://patents.google.com/patent/US12438380B2/en) "Data center system and method of operating the data center system" (granted 2025-10-07; shares priority EP22158675.3 with EP 4236002 B1) | Nlighten HQ B.V. | Grid plus gas-fired power module; electrolyser converts co-located renewable power to gas; PEM fuel cells | No compute-job scheduling, no connection minimisation, no quantum method |
| [US 11,501,194 B2](https://patents.google.com/patent/US11501194B2/en) "Managing computational workloads of computing apparatuses powered by renewable resources" (granted 2022-11-15) | Microsoft Technology Licensing LLC | Schedules compute using predicted renewable output and SLAs | No hydrogen, no connection minimisation, no quantum method |

## Public repositories

| Repository | Own description | Objective | H₂ chain | Workload shifting | Connection envelope | QUBO / QAOA | Licence | Stars |
|---|---|---|---|---|---|---|---|---|
| [dos-group/vessim](https://github.com/dos-group/vessim) | Python library for simulating datacenter energy systems | co-simulation | – | via controllers | GridConnection (limits not documented) | ✗ | MIT | 103 |
| [peaclab/flexdc-sim](https://github.com/peaclab/flexdc-sim) | data-centre demand-response simulator | DR target tracking | – | job placement, power caps | DR power target | ✗ | BSD-3-Clause | 23 |
| [atlarge-research/OpenDC-STEAM](https://github.com/atlarge-research/OpenDC-STEAM) | artifact for the STEAM paper (CCGrid 2026) | sustainability simulation | ✗ | ✓ | ✗ | ✗ | MIT | 1 |
| [Green-Software-Foundation/carbon-aware-sdk](https://github.com/Green-Software-Foundation/carbon-aware-sdk) | toolset to measure software carbon emissions | signals only | ✗ | enables | ✗ | ✗ | MIT | 600 |
| [dos-group/lets-wait-awhile](https://github.com/dos-group/lets-wait-awhile) | simulator and datasets for carbon-aware temporal workload shifting | carbon | ✗ | ✓ | ✗ | ✗ | none | 26 |
| [umassos/CarbonScaler](https://github.com/umassos/CarbonScaler) | cloud workload elasticity for carbon efficiency | carbon | ✗ | elastic scaling | ✗ | ✗ | MIT | 5 |
| [Irieo/space-time-optimization](https://github.com/Irieo/space-time-optimization) | code for "Spatio-temporal load shifting for truly clean computing" | 24/7 CFE cost | – | space + time | ✗ | ✗ | none | 17 |
| [PyPSA/247-cfe](https://github.com/PyPSA/247-cfe) | impacts of 24/7 carbon-free energy PPAs | 24/7 CFE cost | – | – | ✗ | ✗ | MIT | 38 |
| [acnewkirk/AI-Datacenter-Microgrid-Analysis](https://github.com/acnewkirk/AI-Datacenter-Microgrid-Analysis) | datacenter power-system LCOE comparison | LCOE | ✗ | ✗ | grid as baseline | ✗ | MIT | 2 |
| [NatLabRockies/H2Integrate](https://github.com/NatLabRockies/H2Integrate) (formerly NREL/H2Integrate) | hybrid plant model incl. electrolysis and fuel cells | plant design and cost | ✓ | ✗ | ✗ | ✗ | BSD-3-Clause | 32 |
| [PyPSA/PyPSA](https://github.com/PyPSA/PyPSA) | Python for Power System Analysis | general LP/MILP | can model | generic | generic | ✗ | MIT | 2251 |
| [oemof/oemof-solph](https://github.com/oemof/oemof-solph) | energy-system model generator | general LP/MILP | can model | generic | generic | ✗ | none reported by API | 430 |
| [calliope-project/calliope](https://github.com/calliope-project/calliope) | multi-scale energy-systems modelling framework | general | can model | generic | generic | ✗ | Apache-2.0 | 380 |
| [georgiakarataraki/Microgrid-Optimization-Model-with-Hydrogen-Storage](https://github.com/georgiakarataraki/Microgrid-Optimization-Model-with-Hydrogen-Storage) | MILP microgrid with hydrogen storage | cost | ✓ | ✗ | islanded / grid-connected | ✗ | none | 11 |
| [shibmaster/h2simulator](https://github.com/shibmaster/h2simulator) | PV, electrolyser, H₂ tank and fuel-cell simulator | savings / ROI | ✓ | ✗ | ✗ | ✗ | none | 20 |
| [PlanQK/EnergyUnitCommitment](https://github.com/PlanQK/EnergyUnitCommitment) | unit commitment with GLPK, simulated quantum annealing, Qiskit QAOA, D-Wave | unit commitment | ✗ | ✗ | ✗ | ✓ | Apache-2.0 | 3 |
| [ajliouat/quantumgrid](https://github.com/ajliouat/quantumgrid) | QAOA/VQE on ENTSO-E data vs MILP baselines | unit commitment | ✗ | ✗ | ✗ | ✓ | NOASSERTION | 4 |
| [austinamissah/quantum-solar](https://github.com/austinamissah/quantum-solar) | QAOA scheduling of residential solar under time-of-use pricing, verified against exact solvers | cost | ✗ | ✗ | ✗ | ✓ | MIT | 1 |
| [juanfrh7/uc-problem-annealing](https://github.com/juanfrh7/uc-problem-annealing) | unit commitment on D-Wave annealers | unit commitment | ✗ | ✗ | ✗ | annealing | none | 9 |
| [stefanocarrraro/MSc_Thesis_2024](https://github.com/stefanocarrraro/MSc_Thesis_2024) | flexibility in grid-connection capacity planning of urban living spaces | peak grid power | ✗ | EV, heat pumps | fixed transformer limit | ✗ | none | 0 |
| [SINTEF-Power-system-asset-management/flexible_load_analysis](https://github.com/SINTEF-Power-system-asset-management/flexible_load_analysis) | load time series vs transfer capacity | analysis | ✗ | ✗ | transfer capacity | ✗ | GPL-3.0 | 7 |

## Observation

Among the papers, patents and repositories surveyed on 2026-11-21 we did not find one that combines **all**
of: minimisation of the required grid connection; an AI data-centre load with discrete delay-tolerant
bundles; on-site solar and wind with an electrolyser–tank–fuel-cell chain; firm, phased and time-varying
non-firm envelopes; and a QUBO/QAOA formulation of the placement block verified by exhaustive
enumeration. Each element exists elsewhere on its own. The survey is limited (keyword search, English
sources, GitHub only, patent pages read to abstract and claims) and may miss relevant work.

**Search limits.** No public code was found for GAIA (ASPLOS 2024) or Google's Carbon-Intelligent
Computing System; Ecovisor (ASPLOS 2023, [doi:10.1145/3575693.3575709](https://doi.org/10.1145/3575693.3575709))
has a repository without a description ([carbonfirst/Ecovisor](https://github.com/carbonfirst/Ecovisor)).
