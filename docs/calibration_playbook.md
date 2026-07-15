# Calibration Playbook

## Purpose

The current model is scenario-driven and reproducible. To turn it into a production-grade decision-support model, the next step is calibration against real operational event logs.

This document defines how real process data should be mapped into the simulation framework.

## Required Event Log Fields

| Field | Description |
|---|---|
| `item_id` | Unique customer/order/process item identifier |
| `step` | Process step name |
| `queue_enter_time` | Timestamp when the item became ready for the step |
| `service_start_time` | Timestamp when processing actually started |
| `service_end_time` | Timestamp when processing ended |
| `resource_id` | Optional worker, API, machine, or lane identifier |
| `route_flag` | Optional indicator for skipped/routed steps |
| `outcome` | Optional completion, rejection, rework, or exception flag |

## Calibration Steps

1. Compute inter-arrival times from first process-entry timestamps.
2. Estimate arrival-rate seasonality by hour, day, campaign, or order wave.
3. Estimate service-time distributions by step.
4. Compare candidate distributions using visual fit, KS tests, and operational interpretability.
5. Estimate server capacity from concurrent active resource counts.
6. Validate baseline simulation against historical cycle time, p95 cycle time, throughput, SLA breach rate, and queue length.
7. Freeze the calibrated baseline before testing redesigns.

## Recommended Distribution Mapping

| Operational Pattern | Candidate Distribution |
|---|---|
| Memoryless API calls | Exponential |
| Multi-stage automated processing | Erlang or Gamma |
| Human processing with right-tail variability | Lognormal |
| Tightly controlled takt-time operation | Uniform or deterministic |
| Batch waves | Empirical distribution |

## Acceptance Criteria

A calibrated baseline should be considered credible when:

- Mean cycle time error is under 10%.
- p95 cycle time error is under 15%.
- Throughput error is under 10%.
- Bottleneck identity matches the real operation.
- Simulated SLA breach rate is directionally consistent with observed SLA breach rate.

## Extensions

Useful production extensions include:

- Shift schedules and breaks
- Priority classes
- Rework loops
- Customer abandonment
- Batch cutoffs
- Resource pooling
- Time-varying arrivals
- Empirical service-time sampling from historical logs
