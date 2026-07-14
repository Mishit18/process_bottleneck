# Process Bottleneck Analysis

Discrete-event simulation project for operations bottleneck diagnosis, redesign testing, and cost-benefit analysis across two process settings:

- Fintech KYC verification pipeline
- FMCG warehouse pick-and-pack operation

The project combines analytical queueing methods with SimPy-based simulation to identify bottlenecks, compare redesign options, stress-test demand surges, and quantify business impact.

## Highlights

- Analytical bottleneck identification using utilisation, Little's Law, and Erlang-C queueing estimates
- SimPy discrete-event simulation with warmup removal and 10 replications per configuration
- 95% confidence intervals for cycle time, throughput, waits, and queue lengths
- Three redesign options per scenario with demand surge and sensitivity testing
- Cost-benefit analysis with net benefit and payback calculations
- Publication-ready plots and reproducible CSV outputs

## Project Structure

```text
process_bottleneck/
├── scenario_a_kyc.ipynb
├── scenario_b_warehouse.ipynb
├── simulation_framework.py
├── run_analysis.py
├── outputs/
│   ├── results_comparison.csv
│   ├── cost_benefit.csv
│   ├── stress_test.csv
│   └── *.png
└── summary.md
```

## How To Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Regenerate all simulations, plots, CSVs, notebooks, and summary:

```bash
python run_analysis.py
```

The notebooks can also be run top-to-bottom:

```bash
jupyter notebook scenario_a_kyc.ipynb
jupyter notebook scenario_b_warehouse.ipynb
```

## Key Results

- KYC current-state bottleneck: Manual Review, rho=1.07
- KYC best redesign: ML Triage, reducing cycle time by 73.6%
- Warehouse current-state bottleneck: Picking, rho=1.11
- Warehouse best redesign: Zone Picking, reducing cycle time by 64.2%

Full recommendations and resume-ready bullets are in `summary.md`.
