# Process Bottleneck Analysis

## Executive Recommendation
| Scenario | Bottleneck | Current Cycle Time | Recommended Redesign | Cycle-Time Reduction | Net Benefit |
|---|---:|---:|---|---:|---:|
| Fintech KYC | Manual Review, rho=1.07 | 30.3 min | ML Triage | 73.6% | Rs.11384/hr |
| Warehouse | Picking, rho=1.11 | 50.9 min | Zone Picking | 64.2% | Rs.5165/hr |

Both current-state systems have structural bottlenecks with utilisation above 1.0. The recommended interventions are selected by net business benefit after simulation, not by capacity gain alone.

## Fintech KYC Verification Pipeline
- Analytical bottleneck: Manual Review with rho=1.07; theoretical capacity is 112.0 items/hr and pure processing time is 3.44 min.
- Current simulation: cycle time 30.3 min (95% CI 23.8-36.7), throughput 108.1/hr (95% CI 107.0-109.3).
- Best redesign by net benefit: ML Triage. It reduced cycle time by 73.6% and changed throughput by 8.8% versus current state.
- Cost recommendation: ML Triage produces Rs.11384/hr net benefit with payback of 0.07 months.
- Stress test at +50% demand: ML Triage did not meet the collapse rule (average bottleneck queue 0.6, cycle time 78.0 min).
- Sensitivity: ML Triage becomes unstable at not observed in tested range; Add 2 Agents has the widest stable tested demand range up to 1.5x base demand.

## Warehouse Pick-and-Pack
- Analytical bottleneck: Picking with rho=1.11; theoretical capacity is 90.0 items/hr and pure processing time is 8.63 min.
- Current simulation: cycle time 50.9 min (95% CI 41.5-60.3), throughput 85.1/hr (95% CI 84.0-86.3).
- Best redesign by net benefit: Zone Picking. It reduced cycle time by 64.2% and changed throughput by 13.5% versus current state.
- Cost recommendation: Zone Picking produces Rs.5165/hr net benefit with payback of 0.62 months.
- Stress test at +50% demand: Zone Picking did not meet the collapse rule (average bottleneck queue 71.9, cycle time 108.8 min).
- Sensitivity: Zone Picking becomes unstable at not observed in tested range; Add 2 Pickers has the widest stable tested demand range up to 1.5x base demand.

## Erlang-C Validation
Stable exponential steps in the recommended redesigns had mean absolute wait-time error of 9.8% versus Erlang-C analytical estimates.

## Deliverables
- 2 executable scenario notebooks
- 18 generated plots
- Interactive executive dashboard at `outputs/executive_dashboard.html`
- CSV outputs for comparison, cost-benefit, stress testing, sensitivity analysis, SLA KPIs, event logs, and Erlang-C validation
- Reusable SimPy framework with warmup removal, queue monitoring, route fractions, and replication logic

## Resume Bullets
- Modeled fintech KYC pipeline via DES; identified Manual Review bottleneck (rho=1.07); best redesign cut cycle time 74% at zero added headcount.
- Simulated warehouse pick-and-pack; Zone Picking improved throughput 13% with Rs.5165/hr net benefit.
- Validated redesigns under 50% demand surge; base queues diverged to 163+ items, exposing concrete surge-capacity limits.
- Sensitivity analysis showed Add 2 Agents stable up to 150% of base demand; warehouse base unstable beyond 150%.
