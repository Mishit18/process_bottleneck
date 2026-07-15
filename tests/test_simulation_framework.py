import math

import numpy as np

from simulation_framework import (
    SimConfig,
    analyse_process,
    ci95,
    erlang_c,
    run_replications,
    run_simulation,
    sample_service_time,
    theoretical_capacity,
)


def test_erlang_c_returns_infinite_wait_when_unstable():
    p_wait, wq = erlang_c(lam=12, mu=5, c=2)

    assert p_wait == 1.0
    assert math.isinf(wq)


def test_erlang_c_matches_known_mm1_result():
    p_wait, wq = erlang_c(lam=4, mu=5, c=1)

    assert round(p_wait, 3) == 0.8
    assert round(wq, 3) == 0.8


def test_service_time_sampling_is_positive():
    rng = np.random.default_rng(42)
    distributions = ["exponential", "erlang2", "lognormal", "uniform"]

    for dist in distributions:
        samples = [sample_service_time(20, dist, rng) for _ in range(100)]
        assert min(samples) > 0


def test_run_simulation_discards_warmup_items():
    steps = {
        "A": {"mu": 50, "servers": 2, "dist": "exponential", "lambda": 10},
        "B": {"mu": 60, "servers": 1, "dist": "erlang2", "lambda": 10},
    }

    result = run_simulation(SimConfig(steps=steps, arrival_rate=10, num_items=60, warmup_items=10, seed=7))

    assert result.completed_items == 50
    assert len(result.total_cycle_times) == 50
    assert len(result.item_log) == 50
    assert len(result.event_log) >= 100
    assert result.throughput_per_hour > 0
    assert all(len(trace) > 1 for trace in result.step_queue_lengths.values())
    assert {"item_id", "step", "wait_time_min", "service_time_min"}.issubset(result.event_log[0])


def test_replications_return_confidence_interval_metrics():
    steps = {
        "A": {"mu": 80, "servers": 2, "dist": "exponential", "lambda": 20},
        "B": {"mu": 90, "servers": 1, "dist": "uniform", "lambda": 20},
    }

    results = run_replications(
        SimConfig(steps=steps, arrival_rate=20, num_items=80, warmup_items=10, seed=11),
        n_reps=3,
        bottleneck_step="A",
    )

    assert results["cycle_time_min"][0] > 0
    assert results["throughput_hr"][0] > 0
    assert results["bottleneck_queue"][0] >= 0
    assert set(results["wait_times_min"]) == {"A", "B"}


def test_analysis_and_capacity_helpers():
    steps = {
        "Fast": {"mu": 100, "servers": 1, "dist": "exponential", "lambda": 40},
        "Slow": {"mu": 30, "servers": 2, "dist": "lognormal", "lambda": 40},
    }

    analysis = analyse_process(steps)

    assert theoretical_capacity(steps) == 60
    assert analysis.loc[analysis["Step"] == "Slow", "Utilisation_rho"].iloc[0] == 40 / 60
    assert not analysis["Is_Bottleneck"].any()


def test_ci95_handles_single_value():
    mean, interval = ci95([12.5])

    assert mean == 12.5
    assert interval == (12.5, 12.5)
