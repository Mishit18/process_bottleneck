# Interview Guide

## 30-Second Pitch

This project uses discrete-event simulation to diagnose process bottlenecks in two operations settings: fintech KYC onboarding and FMCG warehouse fulfillment. I first identify the overloaded station analytically using utilisation and queueing theory, then validate redesign options with SimPy simulations, confidence intervals, demand stress tests, and cost-benefit analysis.

## What To Emphasize

- The same simulation framework handles both digital operations and physical supply chain workflows.
- Bottlenecks are identified before simulation, which makes the diagnosis explainable.
- Redesigns are compared through business impact, not only operational metrics.
- The results include uncertainty through confidence intervals.
- The project includes reproducibility checks, tests, and CI.

## KYC Talking Points

- Manual Review has rho=1.07, meaning arrival demand exceeds manual review capacity.
- ML Triage reduces effective manual-review load by auto-approving low-risk cases.
- The recommended redesign cuts cycle time by 73.6% with zero added headcount.
- The modeled net benefit is Rs.11,384/hr after operating cost.

## Warehouse Talking Points

- Picking has rho=1.11, making it the structural bottleneck.
- Zone Picking increases picker productivity without immediately adding headcount.
- The recommended redesign cuts cycle time by 64.2%.
- The modeled net benefit is Rs.5,165/hr with a short payback period.

## Questions To Be Ready For

### Why use simulation instead of only queueing theory?

Queueing theory gives a fast bottleneck diagnosis, but simulation handles non-exponential service distributions, route fractions, warmup removal, stochastic variability, redesign comparisons, and stress tests in a single framework.

### Why select by net benefit instead of cycle time?

The best operational redesign should be economically justified. A redesign that reduces cycle time more may still be worse if its operating cost or setup cost erodes the benefit.

### What would be the next production extension?

Add abandonment, rework, staff shifts, SLA breach probabilities, batching windows, and calibrated arrival/service distributions from real timestamp data.

### What makes the result credible?

The project uses replicated simulations, confidence intervals, analytical validation against Erlang-C for stable exponential steps, queue monitoring throughout the run, unit tests, and automated artifact validation.
