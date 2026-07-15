# Portfolio Case Study

## Problem

High-growth operations often fail at the bottleneck: a single overloaded team or workstation silently determines total throughput, SLA performance, and customer experience. This project builds a reusable simulation framework to diagnose that failure mode and test redesign options before committing budget.

## Scenarios

The same framework is applied to two different operating systems:

- Fintech KYC verification: customer onboarding through upload, OCR, liveness, compliance, manual review, and notification.
- Warehouse pick-and-pack: order batching, pick-list generation, picking, quality check, packing, and dispatch.

## Approach

The analysis starts with queueing theory to identify the bottleneck analytically. It then uses discrete-event simulation to validate the finding under stochastic arrivals and service times. Each redesign is tested across 10 replications, with confidence intervals for cycle time and throughput.

## Recommendations

For the KYC process, Manual Review is overloaded at rho=1.07. The strongest business recommendation is ML Triage, which reduces effective manual-review demand and cuts simulated cycle time by 73.6% while avoiding added headcount.

For the warehouse process, Picking is overloaded at rho=1.11. The recommended redesign is Zone Picking, which improves picker productivity and reduces cycle time by 64.2% with a short modeled payback period.

## Business Value

The project translates simulation results into operating recommendations:

- KYC: ML Triage generates an estimated Rs.11,384/hr net benefit.
- Warehouse: Zone Picking generates an estimated Rs.5,165/hr net benefit.
- Demand stress testing exposes how current-state queues diverge under surge conditions.
- Sensitivity analysis provides practical capacity-planning thresholds.
- Item-level event logs and SLA KPIs make the model auditable beyond aggregate averages.
- The interactive dashboard gives an executive view of cycle time, economics, tail risk, and stress behavior.

## Resume Bullets

- Modeled fintech KYC pipeline via DES; identified Manual Review bottleneck (rho=1.07); best redesign cut cycle time 74% at zero added headcount.
- Simulated warehouse pick-and-pack; Zone Picking improved throughput 13% with Rs.5,165/hr net benefit.
- Validated redesigns under 50% demand surge; base queues diverged to 163+ items, exposing concrete surge-capacity limits.
- Sensitivity analysis showed Add 2 Agents stable up to 150% of base demand; warehouse base unstable beyond 150%.
