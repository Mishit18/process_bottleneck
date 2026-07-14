# Methodology

## Objective

The project evaluates two operating systems with a shared discrete-event simulation framework. The goal is to identify process bottlenecks, quantify their business impact, compare feasible redesigns, and test whether recommended changes hold under demand stress.

## Analytical Layer

Each process step is first evaluated using:

- Arrival rate into the step
- Service rate per server
- Number of servers
- Capacity per hour
- Utilisation, computed as lambda / (servers * mu)
- Erlang-C estimates for stable M/M/c-like stations
- Little's Law for queue length and waiting-time interpretation

Steps with utilisation greater than or equal to 1.0 are treated as structurally unstable bottlenecks because long-run demand exceeds long-run capacity.

## Simulation Layer

The simulation is implemented in `simulation_framework.py` with SimPy resources. Each item travels through a serial process, requesting capacity at every step. Service times are sampled from station-specific distributions:

- Exponential for highly variable automated or API-driven steps
- Erlang-2 for lower-variance automated processing
- Lognormal for human workstations with moderate right-tail variability

For KYC triage redesigns, only the routed fraction enters Manual Review. This keeps the simulation consistent with the operational redesign: the triage system reduces actual manual workload, not just the label in the analytical table.

## Replication And Confidence Intervals

Each configuration is simulated with 10 independent replications. Seeds are deterministic and incremented by replication number. The first 150 items are discarded as warmup to reduce transient bias. Metrics are reported as means with 95% Student's t confidence intervals.

Tracked metrics include:

- Total cycle time
- Throughput per hour
- Per-step wait time
- Per-step service time
- Time-weighted queue length
- Bottleneck queue length

## Redesign Logic

Each scenario tests three practical redesigns:

- Add capacity at the bottleneck
- Improve process productivity or reduce effective load
- Combine process redesign with targeted capacity

The best redesign is selected by net business benefit rather than raw cycle-time reduction alone.

## Stress And Sensitivity Testing

Stress testing increases arrival rate by 50%. A configuration is marked as collapsed when both of these are true:

- Average bottleneck queue length exceeds 20 items
- Average cycle time exceeds 120 minutes

Sensitivity tests vary:

- Bottleneck service rate from 80% to 120% of baseline
- Arrival rate from 60% to 150% of baseline

## Validation

Stable exponential stations are compared against Erlang-C wait-time estimates. The generated validation output reports mean absolute percentage error versus the analytical queueing estimate.

The repository also includes automated checks:

- `tests/test_simulation_framework.py` verifies queueing formulas, service-time sampling, warmup removal, replication outputs, and capacity helpers.
- `validate_project.py` checks that all required plots, CSVs, notebooks, documentation files, and validation metrics are present.
- GitHub Actions runs the unit tests and artifact validation on every push and pull request to `main`.

## Limitations

The model is intentionally operational rather than behavioral. It does not include customer abandonment, shift schedules, batch cutoffs, learning curves, rework, or failure modes. Those would be natural extensions for a production decision-support model.
