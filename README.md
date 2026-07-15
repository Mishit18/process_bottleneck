# Process Bottleneck Analysis

[![Validate project](https://github.com/Mishit18/process_bottleneck/actions/workflows/validation.yml/badge.svg)](https://github.com/Mishit18/process_bottleneck/actions/workflows/validation.yml)

Discrete-event simulation and operations research project for diagnosing process bottlenecks, testing redesigns, and translating capacity improvements into business recommendations.

The project models two operating environments with the same reusable SimPy framework:

- Fintech KYC verification pipeline, framed for digital banking and Revolut-style onboarding operations
- FMCG warehouse pick-and-pack process, framed for P&G/ITC-style distribution operations

![KYC process flow](outputs/kyc_plot_01_process_flow.png)

## Executive Results

| Scenario | Bottleneck | Current Cycle Time | Recommended Redesign | Cycle Time Reduction | Net Benefit |
|---|---:|---:|---|---:|---:|
| Fintech KYC | Manual Review, rho=1.07 | 30.3 min | ML Triage | 73.6% | Rs.11,384/hr |
| Warehouse | Picking, rho=1.11 | 50.9 min | Zone Picking | 64.2% | Rs.5,165/hr |

The current-state bottlenecks are overloaded in both scenarios, with utilisation above 1.0. The redesigns reduce effective bottleneck load or improve service productivity, then the project validates the changes through replicated simulation, demand stress tests, sensitivity analysis, and cost-benefit modeling.

## What This Demonstrates

- Analytical bottleneck identification using utilisation, Little's Law, and Erlang-C queueing estimates
- SimPy discrete-event simulation with route logic, finite-capacity resources, warmup removal, and queue monitoring
- 10 replications per configuration with 95% confidence intervals
- Three redesign options per scenario, including headcount, process redesign, and automation/triage choices
- Demand stress tests at +50% arrival rate
- Sensitivity analysis for arrival rate and bottleneck productivity
- Cost-benefit analysis with payback and hourly net benefit
- 18 publication-quality plots plus reproducible CSV outputs
- Item-level event logs, SLA breach metrics, and p95/p99 cycle-time KPIs
- Interactive HTML dashboard for executive review
- Unit tests and GitHub Actions validation for reproducibility checks

## Repository Structure

```text
process_bottleneck/
|-- scenario_a_kyc.ipynb
|-- scenario_b_warehouse.ipynb
|-- simulation_framework.py
|-- run_analysis.py
|-- validate_project.py
|-- pyproject.toml
|-- summary.md
|-- tests/
|   `-- test_simulation_framework.py
|-- docs/
|   |-- calibration_playbook.md
|   |-- methodology.md
|   |-- interview_guide.md
|   `-- portfolio_case_study.md
|-- .github/
|   `-- workflows/validation.yml
|-- outputs/
|   |-- results_comparison.csv
|   |-- cost_benefit.csv
|   |-- stress_test.csv
|   |-- kpi_summary.csv
|   |-- event_log_sample.csv
|   |-- executive_dashboard.html
|   |-- erlang_c_validation.csv
|   `-- *.png
`-- requirements.txt
```

## How To Run

Create an environment and install dependencies:

```bash
pip install -r requirements.txt
```

Regenerate simulations, plots, CSVs, notebooks, and summary:

```bash
python run_analysis.py
```

Validate the generated project artifacts:

```bash
python validate_project.py
```

Run the test suite:

```bash
pytest
```

Open the scenario notebooks:

```bash
jupyter notebook scenario_a_kyc.ipynb
jupyter notebook scenario_b_warehouse.ipynb
```

## Selected Visuals

### Fintech KYC: Queue Growth vs. Redesign

![KYC queue growth](outputs/kyc_plot_02_queue_growth.png)

### Warehouse: Cycle Time Comparison

![Warehouse cycle time comparison](outputs/warehouse_plot_03_cycle_time_comparison.png)

### Warehouse: Queue Stability Comparison

![Warehouse queue stability](outputs/warehouse_plot_10_queue_panels.png)

## Interactive Dashboard

The generated file `outputs/executive_dashboard.html` provides an interactive review of:

- Mean cycle time with confidence intervals
- Redesign economics
- p95 cycle-time risk versus SLA
- +50% demand stress-test bottleneck queues

## Key Files

- `simulation_framework.py`: reusable DES engine, service-time sampling, Erlang-C analysis, replication logic
- `run_analysis.py`: scenario definitions, redesign experiments, sensitivity tests, cost-benefit logic, plot generation
- `validate_project.py`: artifact quality gate for CSVs, plots, notebooks, docs, and validation thresholds
- `tests/test_simulation_framework.py`: unit tests for queueing helpers, simulation behavior, warmup removal, and replication outputs
- `summary.md`: final quantified recommendations and resume-ready bullets
- `docs/methodology.md`: modeling assumptions, validation approach, and limitations
- `docs/calibration_playbook.md`: schema and steps for calibrating the simulation with real operational logs
- `docs/portfolio_case_study.md`: interview-friendly explanation of the project and business impact
- `docs/interview_guide.md`: short pitch, talking points, and likely interview questions

## Reproducibility

Random seeds are fixed and incremented by replication. The first 150 items are discarded as warmup in every run. Queue lengths are monitored every 0.01 simulation hours. Confidence intervals use `scipy.stats.t.interval`.
