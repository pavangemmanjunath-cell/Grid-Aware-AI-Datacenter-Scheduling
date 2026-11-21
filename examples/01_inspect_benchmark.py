"""Example 1 - what is in the 168-hour benchmark?  (runtime < 1 s)

Reads data/research_benchmark_168h.csv and prints the ranges quoted in data/README.md,
the envelopes, and the grid-only reference R0 (which needs no optimisation: import
equals demand, so its peak is the firm connection a campus would request today).

    python examples/01_inspect_benchmark.py
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
d = pd.read_csv(DATA / "research_benchmark_168h.csv")

print("Synthetic benchmark: %d hourly rows (%d days)\n" % (len(d), d.day.nunique()))
rows = [
    ("Latency-sensitive AI demand", "fixed_ai_load_MW", "MW"),
    ("Delay-tolerant bundles (baseline)", "baseline_flexible_load_MW", "MW"),
    ("Solar", "solar_MW", "MW"),
    ("Wind", "wind_MW", "MW"),
    ("Grid carbon intensity", "grid_carbon_kgCO2_per_MWh", "kg/MWh"),
]
print(f"{'signal':<36}{'min':>9}{'max':>9}{'mean':>9}")
for name, col, unit in rows:
    s = d[col]
    print(f"{name:<36}{s.min():>9.3f}{s.max():>9.3f}{s.mean():>9.3f}  {unit}")

print("\nFlexible bundles:", int((d.baseline_flexible_load_MW > 0).sum()),
      "| baseline hours of day:", sorted(d.loc[d.baseline_flexible_load_MW > 0, "hour_of_day"].unique().tolist()))
print("Non-firm envelope levels:", sorted(d.nonfirm_connection_cap_MW.unique().tolist()),
      "MW | constrained hours:", int(d.nonfirm_constraint_event.sum()))
print("Phased envelope levels:", sorted(d.phased_connection_cap_MW.unique().tolist()), "MW")

load = d.fixed_ai_load_MW + d.baseline_flexible_load_MW
print(f"\nR0 grid-only reference: peak {load.max():.2f} MW, energy {load.sum():.2f} MWh, "
      f"CO2 {(load * d.grid_carbon_kgCO2_per_MWh).sum() / 1000:.2f} t")
