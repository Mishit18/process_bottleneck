import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import simpy
from scipy import stats

warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)


@dataclass
class SimConfig:
    steps: Dict
    arrival_rate: float
    num_items: int = 1000
    warmup_items: int = 150
    seed: int = 42
    monitor_interval: float = 0.01


@dataclass
class SimResults:
    step_wait_times: Dict[str, List[float]] = field(default_factory=dict)
    step_service_times: Dict[str, List[float]] = field(default_factory=dict)
    step_queue_lengths: Dict[str, List[Tuple[float, int]]] = field(default_factory=dict)
    total_cycle_times: List[float] = field(default_factory=list)
    throughput_per_hour: float = 0.0
    completed_items: int = 0
    first_measured_arrival: float = 0.0
    last_measured_completion: float = 0.0
    arrival_end_time: float = 0.0


def erlang_c(lam: float, mu: float, c: int) -> Tuple[float, float]:
    """Return Erlang-C probability of wait and expected queue wait in hours."""
    rho = lam / (c * mu)
    if rho >= 1:
        return 1.0, float("inf")

    a = lam / mu
    sum_terms = sum((a**k) / math.factorial(k) for k in range(c))
    last_term = (a**c) / (math.factorial(c) * (1 - rho))
    p_wait = last_term / (sum_terms + last_term)
    wq = p_wait / (c * mu - lam)
    return p_wait, wq


def analyse_process(steps: dict) -> pd.DataFrame:
    """Compute utilisation and Little's Law metrics for each process step."""
    rows = []
    for step_name, params in steps.items():
        lam = params.get("lambda", params.get("effective_lambda", 0))
        mu = params["mu"]
        c = params["servers"]
        rho = lam / (c * mu)
        p_wait, wq = erlang_c(lam, mu, c)
        lq = lam * wq if math.isfinite(wq) else float("inf")
        w = wq + 1 / mu if math.isfinite(wq) else float("inf")
        l = lam * w if math.isfinite(w) else float("inf")
        rows.append(
            {
                "Step": step_name,
                "Lambda_in": lam,
                "Mu_per_server": mu,
                "Servers": c,
                "Capacity_per_hr": c * mu,
                "Utilisation_rho": rho,
                "P_wait": p_wait,
                "Avg_Queue_Length": lq,
                "Avg_Wait_Time_min": wq * 60 if math.isfinite(wq) else float("inf"),
                "Avg_Cycle_Time_min": w * 60 if math.isfinite(w) else float("inf"),
                "Avg_Items_in_System": l,
                "Is_Bottleneck": rho >= 1.0,
            }
        )
    return pd.DataFrame(rows)


def theoretical_capacity(steps: dict) -> float:
    return min(params["servers"] * params["mu"] for params in steps.values())


def theoretical_process_time_min(steps: dict) -> float:
    return sum(1 / params["mu"] for params in steps.values()) * 60


def sample_service_time(mu: float, dist: str, rng: np.random.Generator) -> float:
    """Sample service time in hours from the configured distribution."""
    mean_service = 1.0 / mu
    if dist == "exponential":
        return rng.exponential(mean_service)
    if dist == "erlang2":
        return rng.exponential(mean_service / 2) + rng.exponential(mean_service / 2)
    if dist == "lognormal":
        cv = 0.5
        sigma = np.sqrt(np.log(1 + cv**2))
        mu_ln = np.log(mean_service) - sigma**2 / 2
        return rng.lognormal(mu_ln, sigma)
    if dist == "uniform":
        return rng.uniform(mean_service * 0.5, mean_service * 1.5)
    return rng.exponential(mean_service)


def run_simulation(config: SimConfig) -> SimResults:
    rng = np.random.default_rng(config.seed)
    env = simpy.Environment()
    results = SimResults()

    for step_name in config.steps:
        results.step_wait_times[step_name] = []
        results.step_service_times[step_name] = []
        results.step_queue_lengths[step_name] = []

    resources = {
        name: simpy.Resource(env, capacity=params["servers"])
        for name, params in config.steps.items()
    }

    completed_counter = [0]
    first_measured_arrival = [None]
    last_measured_completion = [None]
    arrival_end_time = [0.0]
    done = [False]

    def monitor_queue(resource, step_name):
        while not done[0]:
            results.step_queue_lengths[step_name].append((env.now, len(resource.queue)))
            yield env.timeout(config.monitor_interval)
        results.step_queue_lengths[step_name].append((env.now, len(resource.queue)))

    def process_item(item_id):
        arrival_time = env.now
        is_warmup = item_id < config.warmup_items
        if not is_warmup and first_measured_arrival[0] is None:
            first_measured_arrival[0] = arrival_time

        for step_name, step_params in config.steps.items():
            route_fraction = step_params.get("route_fraction", 1.0)
            if route_fraction < 1.0 and rng.random() > route_fraction:
                continue

            req = resources[step_name].request()
            wait_start = env.now
            yield req
            wait_end = env.now

            service_time = sample_service_time(
                step_params["mu"], step_params.get("dist", "exponential"), rng
            )
            yield env.timeout(service_time)
            resources[step_name].release(req)

            if not is_warmup:
                results.step_wait_times[step_name].append(wait_end - wait_start)
                results.step_service_times[step_name].append(service_time)

        if not is_warmup:
            results.total_cycle_times.append(env.now - arrival_time)
            completed_counter[0] += 1
            last_measured_completion[0] = env.now

    def item_generator():
        item_processes = []
        for i in range(config.num_items):
            item_processes.append(env.process(process_item(i)))
            inter_arrival = rng.exponential(1.0 / config.arrival_rate)
            yield env.timeout(inter_arrival)
        arrival_end_time[0] = env.now
        if item_processes:
            yield env.all_of(item_processes)
        done[0] = True

    for step_name in config.steps:
        env.process(monitor_queue(resources[step_name], step_name))

    env.process(item_generator())
    env.run()

    results.completed_items = completed_counter[0]
    results.first_measured_arrival = first_measured_arrival[0] or 0.0
    results.last_measured_completion = last_measured_completion[0] or 0.0
    results.arrival_end_time = arrival_end_time[0]
    if results.last_measured_completion > results.first_measured_arrival:
        results.throughput_per_hour = completed_counter[0] / (
            results.last_measured_completion - results.first_measured_arrival
        )
    return results


def ci95(data):
    data = np.array(data, dtype=float)
    data = data[np.isfinite(data)]
    if len(data) == 0:
        return float("nan"), (float("nan"), float("nan"))
    if len(data) == 1 or np.isclose(np.std(data, ddof=1), 0):
        mean = float(data.mean())
        return mean, (mean, mean)
    interval = stats.t.interval(0.95, len(data) - 1, loc=data.mean(), scale=stats.sem(data))
    return float(data.mean()), (float(interval[0]), float(interval[1]))


def time_weighted_queue_mean(queue_trace: List[Tuple[float, int]]) -> float:
    if len(queue_trace) < 2:
        return 0.0
    total = 0.0
    horizon = queue_trace[-1][0] - queue_trace[0][0]
    if horizon <= 0:
        return 0.0
    for (t0, q0), (t1, _) in zip(queue_trace[:-1], queue_trace[1:]):
        total += q0 * (t1 - t0)
    return total / horizon


def run_replications(config: SimConfig, n_reps: int = 10, bottleneck_step: str = None) -> Dict:
    """Run replications with seed + rep and return means with 95% CIs."""
    all_cycle_times = []
    all_throughputs = []
    all_wait_times = {step: [] for step in config.steps}
    all_queue_means = {step: [] for step in config.steps}
    raw_results = []

    for rep in range(n_reps):
        rep_config = SimConfig(**{**config.__dict__, "seed": config.seed + rep})
        res = run_simulation(rep_config)
        raw_results.append(res)
        all_cycle_times.append(np.mean(res.total_cycle_times) * 60)
        all_throughputs.append(res.throughput_per_hour)
        for step in config.steps:
            waits = res.step_wait_times[step]
            all_wait_times[step].append(np.mean(waits) * 60 if waits else 0.0)
            all_queue_means[step].append(time_weighted_queue_mean(res.step_queue_lengths[step]))

    bottleneck_queue = None
    if bottleneck_step:
        bottleneck_queue = ci95(all_queue_means[bottleneck_step])

    return {
        "cycle_time_min": ci95(all_cycle_times),
        "throughput_hr": ci95(all_throughputs),
        "wait_times_min": {step: ci95(all_wait_times[step]) for step in config.steps},
        "queue_lengths": {step: ci95(all_queue_means[step]) for step in config.steps},
        "bottleneck_queue": bottleneck_queue,
        "raw_cycle_times": all_cycle_times,
        "raw_throughputs": all_throughputs,
        "raw_results": raw_results,
    }
