# Data flow

How data moves from the benchmark file to every number on screen. All diagrams are Mermaid and render on
GitHub.

## 1. End to end

```mermaid
flowchart TB
  subgraph SRC["Source data (versioned in git)"]
    GEN["matlab/qh2dc_build_benchmark.m<br/>seed 20260430"] --> CSV[("data/research_benchmark_168h.csv<br/>168 h · synthetic")]
  end

  subgraph GATE["Validation gate (identical in all implementations)"]
    V1{"168 rows?<br/>total = fixed + flexible?<br/>renewable = solar + wind?"}
  end
  CSV --> V1

  subgraph REF["Reference implementations (not modified here)"]
    M["MATLAB<br/>main_qh2dc.m"]
    P["Python/SciPy<br/>verify_python.py"]
  end
  V1 --> M & P
  M --> PUB[("data/research_results_gridflex.csv<br/>data/verification_summary.json")]
  P --> PUB

  subgraph WEB["Web platform"]
    ENG["Engine<br/>app/engine"] --> API["FastAPI /api/v1"]
    SNAP[("public/data/qh2dc.json<br/>static snapshot")]
    UI["React + three.js app"]
  end
  V1 --> ENG
  PUB -- "published table, read verbatim" --> API
  ENG -- "scripts/export_static_snapshot.py" --> SNAP
  API -- "JSON (live mode)" --> UI
  SNAP -- "JSON (offline mode)" --> UI

  subgraph QA["Quality gates"]
    T1["crosscheck.py · 64 values"]
    T2["engine parity · 6 scenarios + 2 QAOA depths"]
    T3["snapshot = published table"]
    T4["PennyLane gate-level QAOA"]
  end
  PUB -.-> T1 & T2 & T3 & T4
```

## 2. Inside one scheduling run

```mermaid
flowchart LR
  B["Hourly table<br/>d_LS, bundles E_j, solar, wind, CI, envelope"] --> C["Candidate slots<br/>t0, t0+3, t0+7"]
  C --> MILP["MILP<br/>variables g, e, f, c, h, x<br/>balance · inventory · one-hot · renewable backing<br/>min carbon + curtailment + cycling + deferral"]
  MILP -->|feasible?| BIS{"Bisection on C<br/>24 steps"}
  BIS -->|tighten / relax| MILP
  BIS --> OP["Operating point solved AT reported C"]
  OP --> MET["Metrics<br/>capacity · violation · unserved · CO₂ · renewable use · deferral"]
```

## 3. Quantum placement branch

```mermaid
flowchart LR
  D["Day-0 bundles (4) × slots (3)"] --> Q["QUBO builder<br/>stress · carbon · renewables · deferral · one-hot · collision"]
  Q --> E["Enumerate 4,096 states<br/>81 feasible · exact optimum"]
  Q --> I["Ising: x = (1−Z)/2"]
  I --> S["QAOA state vector<br/>p = 1, 2"]
  S --> CMP{"Most probable feasible<br/>= exact optimum?"}
  E --> CMP
```

## 4. Web request flow (Design studio)

```mermaid
sequenceDiagram
  actor U as User
  participant W as Web app
  participant A as FastAPI
  participant J as Job runner
  participant E as Engine
  U->>W: configure components, press "Optimise campus"
  W->>A: POST /api/v1/simulations (validated by Pydantic)
  A->>J: submit
  A-->>W: 202 {id, status: queued}
  J->>E: scale benchmark, build PlantConfig, solve (bisection or envelope)
  loop poll every 350 ms
    W->>A: GET /api/v1/simulations/{id}
    A-->>W: {status, progress}
  end
  E-->>J: schedule + metrics
  A-->>W: {status: succeeded, result: {exploratory: true, ...}}
  W-->>U: comparison with the paper scenario + charts
```

## 5. Dashboard read path

```mermaid
flowchart LR
  F[("data/*.csv · data/dispatch/*.csv · verification_summary.json")] --> R["Research API /api/...<br/>read-only · ETag · 400 on bad scenario"]
  R --> V["Five views<br/>Campus · Connection · Week replay · Quantum check · Evidence"]
  R -- "python -m app.snapshot" --> S[("public/api-snapshot/*.json<br/>identical responses")]
  S --> V
  V --> C["Citation chip on every KPI and chart<br/>paper anchor + CSV column"]
```

## 6. What leaves the machine

Nothing. No component calls an external service at runtime. The public datasets in
[data/README.md](../data/README.md) are **not connected**; they are listed as candidate sources for a
future real-data study. The language-model interface is disabled.
