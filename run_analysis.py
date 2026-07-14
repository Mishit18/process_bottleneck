import json
import math
from copy import deepcopy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import gaussian_kde

from simulation_framework import (
    SEED,
    SimConfig,
    analyse_process,
    erlang_c,
    run_replications,
    run_simulation,
    theoretical_capacity,
    theoretical_process_time_min,
    time_weighted_queue_mean,
)

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 180,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
    }
)
sns.set_theme(style="whitegrid", font_scale=0.9)

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


KYC_STEPS_BASE = {
    "Document Upload": {"mu": 600, "servers": 1, "dist": "exponential", "lambda": 120},
    "OCR Extraction": {"mu": 240, "servers": 1, "dist": "erlang2", "lambda": 120},
    "Liveness Check": {"mu": 180, "servers": 1, "dist": "exponential", "lambda": 120},
    "Compliance Screen": {"mu": 130, "servers": 1, "dist": "exponential", "lambda": 120},
    "Manual Review": {"mu": 28, "servers": 4, "dist": "lognormal", "lambda": 120},
    "Decision & Notify": {"mu": 400, "servers": 1, "dist": "exponential", "lambda": 120},
}
KYC_REDESIGN_A = deepcopy(KYC_STEPS_BASE)
KYC_REDESIGN_A["Manual Review"] = {"mu": 28, "servers": 6, "dist": "lognormal", "lambda": 120}
KYC_REDESIGN_B = deepcopy(KYC_STEPS_BASE)
KYC_REDESIGN_B["Manual Review"] = {
    "mu": 28,
    "servers": 4,
    "dist": "lognormal",
    "lambda": 72,
    "route_fraction": 0.6,
}
KYC_REDESIGN_C = deepcopy(KYC_STEPS_BASE)
KYC_REDESIGN_C["Manual Review"] = {
    "mu": 28,
    "servers": 5,
    "dist": "lognormal",
    "lambda": 72,
    "route_fraction": 0.6,
}

WH_STEPS_BASE = {
    "Order Batching": {"mu": 500, "servers": 1, "dist": "exponential", "lambda": 100},
    "Pick List Gen": {"mu": 250, "servers": 1, "dist": "erlang2", "lambda": 100},
    "Picking": {"mu": 18, "servers": 5, "dist": "lognormal", "lambda": 100},
    "Quality Check": {"mu": 35, "servers": 3, "dist": "erlang2", "lambda": 100},
    "Packing": {"mu": 22, "servers": 5, "dist": "lognormal", "lambda": 100},
    "Dispatch": {"mu": 120, "servers": 1, "dist": "exponential", "lambda": 100},
}
WH_REDESIGN_A = deepcopy(WH_STEPS_BASE)
WH_REDESIGN_A["Picking"] = {"mu": 18, "servers": 7, "dist": "lognormal", "lambda": 100}
WH_REDESIGN_B = deepcopy(WH_STEPS_BASE)
WH_REDESIGN_B["Picking"] = {"mu": 24.3, "servers": 5, "dist": "lognormal", "lambda": 100}
WH_REDESIGN_C = deepcopy(WH_STEPS_BASE)
WH_REDESIGN_C["Picking"] = {"mu": 24.3, "servers": 6, "dist": "lognormal", "lambda": 100}


def clone_with_arrival(steps, arrival_rate, bottleneck_name):
    updated = deepcopy(steps)
    for name, params in updated.items():
        route_fraction = params.get("route_fraction", 1.0)
        params["lambda"] = arrival_rate * route_fraction if name == bottleneck_name else arrival_rate
    return updated


def fmt_ci(metric):
    mean, interval = metric
    return f"{mean:.1f} [{interval[0]:.1f}, {interval[1]:.1f}]"


def interval_width(metric):
    return metric[1][1] - metric[1][0]


def config_rows(scenario_name, scenario_key, configs, results, bottleneck):
    rows = []
    for label, steps in configs.items():
        analytical = analyse_process(steps)
        sim = results[label]
        cycle = sim["cycle_time_min"]
        throughput = sim["throughput_hr"]
        bq = sim["bottleneck_queue"]
        bottleneck_rho = float(analytical.loc[analytical["Step"] == bottleneck, "Utilisation_rho"].iloc[0])
        rows.append(
            {
                "scenario": scenario_name,
                "scenario_key": scenario_key,
                "config": label,
                "bottleneck_step": bottleneck,
                "bottleneck_rho": bottleneck_rho,
                "capacity_per_hr": theoretical_capacity(steps),
                "theoretical_process_time_min": theoretical_process_time_min(steps),
                "cycle_time_min_mean": cycle[0],
                "cycle_time_min_ci_low": cycle[1][0],
                "cycle_time_min_ci_high": cycle[1][1],
                "throughput_hr_mean": throughput[0],
                "throughput_hr_ci_low": throughput[1][0],
                "throughput_hr_ci_high": throughput[1][1],
                "bottleneck_queue_mean": bq[0],
                "bottleneck_queue_ci_low": bq[1][0],
                "bottleneck_queue_ci_high": bq[1][1],
            }
        )
    return rows


def run_config_set(configs, arrival_rate, bottleneck, n_reps=10):
    results = {}
    for label, steps in configs.items():
        cfg = SimConfig(steps=steps, arrival_rate=arrival_rate, seed=SEED)
        results[label] = run_replications(cfg, n_reps=n_reps, bottleneck_step=bottleneck)
    return results


def evaluate_stress(configs, base_arrival, bottleneck, n_reps=10):
    stress_rate = base_arrival * 1.5
    stress_configs = {
        label: clone_with_arrival(steps, stress_rate, bottleneck) for label, steps in configs.items()
    }
    stress_results = run_config_set(stress_configs, stress_rate, bottleneck, n_reps=n_reps)
    rows = []
    for label, res in stress_results.items():
        avg_q = res["bottleneck_queue"][0]
        cycle = res["cycle_time_min"][0]
        rows.append(
            {
                "config": label,
                "arrival_rate": stress_rate,
                "cycle_time_min": cycle,
                "throughput_hr": res["throughput_hr"][0],
                "bottleneck_queue": avg_q,
                "collapsed": bool(avg_q > 20 and cycle > 120),
            }
        )
    return stress_configs, stress_results, pd.DataFrame(rows)


def kyc_costs(results):
    base_t = results["Current State"]["throughput_hr"][0]
    rows = []
    specs = {
        "Add 2 Agents": (1000, 0, 0),
        "ML Triage": (0, 15, 200000),
        "Triage + 1 Agent": (500, 15, 200000),
    }
    for label, (headcount_cost, ml_cost, setup) in specs.items():
        improvement = max(0, results[label]["throughput_hr"][0] - base_t)
        revenue_recovered = improvement * 1200
        total_cost = headcount_cost + ml_cost
        net = revenue_recovered - total_cost
        payback_hours = setup / net if setup and net > 0 else 0
        rows.append(
            {
                "config": label,
                "additional_cost_hr": total_cost,
                "throughput_improvement_hr": improvement,
                "revenue_recovered_hr": revenue_recovered,
                "net_benefit_hr": net,
                "payback_hours": payback_hours,
                "payback_months": payback_hours / (10 * 25) if payback_hours else 0,
            }
        )
    return pd.DataFrame(rows)


def wh_costs(results):
    base_t = results["Current State"]["throughput_hr"][0]
    rows = []
    specs = {
        "Add 2 Pickers": (500, 0),
        "Zone Picking": (0, 800000),
        "Zone + 1 Picker": (250, 800000),
    }
    for label, (hourly_cost, setup) in specs.items():
        improvement = max(0, results[label]["throughput_hr"][0] - base_t)
        revenue_recovered = improvement * 450
        net = revenue_recovered - hourly_cost
        annual = net * 10 * 300
        payback_hours = setup / net if setup and net > 0 else 0
        rows.append(
            {
                "config": label,
                "additional_cost_hr": hourly_cost,
                "throughput_improvement_hr": improvement,
                "revenue_recovered_hr": revenue_recovered,
                "net_benefit_hr": net,
                "annual_net_benefit": annual,
                "payback_hours": payback_hours,
                "payback_months": payback_hours / (10 * 25) if payback_hours else 0,
            }
        )
    return pd.DataFrame(rows)


def best_by_net(cost_df):
    return cost_df.sort_values("net_benefit_hr", ascending=False).iloc[0]["config"]


def plot_process_flow(name, steps, out_path):
    analysis = analyse_process(steps)
    fig, ax = plt.subplots(figsize=(13, 3.2))
    ax.set_xlim(-0.5, len(analysis) - 0.5)
    ax.set_ylim(0, 1)
    ax.axis("off")
    colors = []
    for rho in analysis["Utilisation_rho"]:
        if rho < 0.7:
            colors.append("#2ca25f")
        elif rho < 1.0:
            colors.append("#f0c419")
        else:
            colors.append("#d95f5f")
    for i, row in analysis.iterrows():
        rect = mpatches.FancyBboxPatch(
            (i - 0.38, 0.35),
            0.76,
            0.3,
            boxstyle="round,pad=0.03,rounding_size=0.02",
            facecolor=colors[i],
            edgecolor="#333333",
            linewidth=1.2,
        )
        ax.add_patch(rect)
        label = row["Step"].replace(" ", "\n")
        ax.text(i, 0.53, label, ha="center", va="center", color="white", fontweight="bold", fontsize=8)
        ax.text(i, 0.30, f"rho={row['Utilisation_rho']:.2f}", ha="center", va="center", fontsize=9)
        if i < len(analysis) - 1:
            ax.annotate("", xy=(i + 0.55, 0.50), xytext=(i + 0.40, 0.50), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title(f"{name}: process flow with utilisation colour coding", pad=14, fontweight="bold")
    legend_handles = [
        mpatches.Patch(color="#2ca25f", label="rho < 0.70"),
        mpatches.Patch(color="#f0c419", label="0.70 <= rho < 1.00"),
        mpatches.Patch(color="#d95f5f", label="rho >= 1.00"),
    ]
    ax.legend(handles=legend_handles, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.05), frameon=False)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_queue_growth(prefix, name, base_steps, best_steps, arrival_rate, bottleneck, out_path):
    base = run_simulation(SimConfig(base_steps, arrival_rate, seed=302))
    best = run_simulation(SimConfig(best_steps, arrival_rate, seed=302))
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, res, color in [("Current State", base, "#d95f5f"), ("Best Redesign", best, "#2ca25f")]:
        trace = pd.DataFrame(res.step_queue_lengths[bottleneck], columns=["time_hr", "queue"])
        ax.plot(trace["time_hr"], trace["queue"], label=f"{label} (peak {trace['queue'].max():.0f})", color=color, lw=2)
    ax.set_title(f"{name}: queue length over simulation time at {bottleneck}", fontweight="bold")
    ax.set_xlabel("Simulation time (hours)")
    ax.set_ylabel("Queue length")
    ax.legend()
    ax.annotate("Base queue diverges", xy=(trace["time_hr"].iloc[-1] * 0.7, max(5, trace["queue"].max() * 0.75)))
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_cycle_bars(name, results, sla_min, out_path):
    rows = []
    for label, res in results.items():
        mean, ci = res["cycle_time_min"]
        rows.append({"config": label, "mean": mean, "low": ci[0], "high": ci[1]})
    df = pd.DataFrame(rows).sort_values("mean")
    fig, ax = plt.subplots(figsize=(8, 5))
    yerr = [df["mean"] - df["low"], df["high"] - df["mean"]]
    ax.bar(df["config"], df["mean"], yerr=yerr, capsize=5, color=sns.color_palette("Set2", len(df)))
    ax.axhline(sla_min, color="#333333", ls="--", label=f"SLA target {sla_min} min")
    best = df.iloc[0]
    ax.annotate(f"Best: {best['mean']:.1f} min", xy=(0, best["mean"]), xytext=(0.2, best["mean"] + sla_min * 0.05))
    ax.set_title(f"{name}: cycle time comparison with 95% CI", fontweight="bold")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Mean cycle time (minutes)")
    ax.tick_params(axis="x", rotation=20)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_wait_breakdown(name, results, current_label, best_label, out_path):
    rows = []
    for label in [current_label, best_label]:
        for step, metric in results[label]["wait_times_min"].items():
            rows.append({"config": label, "step": step, "wait_min": metric[0]})
    df = pd.DataFrame(rows)
    pivot = df.pivot(index="config", columns="step", values="wait_min").fillna(0)
    fig, ax = plt.subplots(figsize=(9, 5))
    pivot.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    totals = pivot.sum(axis=1)
    for i, val in enumerate(totals):
        ax.text(i, val, f"{val:.1f} min", ha="center", va="bottom", fontsize=9)
    ax.set_title(f"{name}: per-step wait time breakdown", fontweight="bold")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Mean waiting time (minutes)")
    ax.legend(title="Step", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_throughput_violin(name, results, out_path):
    rows = []
    for label, res in results.items():
        for value in res["raw_throughputs"]:
            rows.append({"config": label, "throughput": value})
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.violinplot(data=df, x="config", y="throughput", inner="box", ax=ax, palette="Set2")
    ax.set_title(f"{name}: throughput distribution across 10 replications", fontweight="bold")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Throughput (items/hour)")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def run_mu_sensitivity(configs, base_arrival, bottleneck, best_label):
    rows = []
    for label in ["Current State", best_label]:
        for mult in [0.8, 0.9, 1.0, 1.1, 1.2]:
            steps = deepcopy(configs[label])
            steps[bottleneck]["mu"] *= mult
            res = run_replications(SimConfig(steps, base_arrival, seed=500 + int(mult * 100)), 10, bottleneck)
            rows.append(
                {
                    "config": label,
                    "mu_multiplier": mult,
                    "cycle_mean": res["cycle_time_min"][0],
                    "cycle_low": res["cycle_time_min"][1][0],
                    "cycle_high": res["cycle_time_min"][1][1],
                    "queue_mean": res["bottleneck_queue"][0],
                    "unstable": bool(res["bottleneck_queue"][0] > 20 and res["cycle_time_min"][0] > 120),
                }
            )
    return pd.DataFrame(rows)


def run_arrival_sensitivity(configs, base_arrival, bottleneck):
    rows = []
    for label, base_steps in configs.items():
        for mult in [0.6, 0.8, 1.0, 1.2, 1.5]:
            rate = base_arrival * mult
            steps = clone_with_arrival(base_steps, rate, bottleneck)
            res = run_replications(SimConfig(steps, rate, seed=700 + int(mult * 100)), 10, bottleneck)
            rows.append(
                {
                    "config": label,
                    "arrival_multiplier": mult,
                    "arrival_rate": rate,
                    "throughput_mean": res["throughput_hr"][0],
                    "throughput_low": res["throughput_hr"][1][0],
                    "throughput_high": res["throughput_hr"][1][1],
                    "queue_mean": res["bottleneck_queue"][0],
                    "cycle_mean": res["cycle_time_min"][0],
                    "unstable": bool(res["bottleneck_queue"][0] > 20 and res["cycle_time_min"][0] > 120),
                }
            )
    return pd.DataFrame(rows)


def plot_mu_sensitivity(name, df, out_path):
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, grp in df.groupby("config"):
        ax.plot(grp["mu_multiplier"], grp["cycle_mean"], marker="o", lw=2, label=label)
        ax.fill_between(grp["mu_multiplier"], grp["cycle_low"], grp["cycle_high"], alpha=0.15)
    ax.set_title(f"{name}: cycle time sensitivity to bottleneck productivity", fontweight="bold")
    ax.set_xlabel("Bottleneck mu multiplier")
    ax.set_ylabel("Cycle time (minutes)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_arrival_sensitivity(name, df, out_path):
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, grp in df.groupby("config"):
        ax.plot(grp["arrival_rate"], grp["throughput_mean"], marker="o", lw=2, label=label)
        unstable = grp[grp["unstable"]]
        if not unstable.empty:
            first = unstable.iloc[0]
            ax.scatter(first["arrival_rate"], first["throughput_mean"], s=90, marker="x", color="black")
    ax.plot(df["arrival_rate"].sort_values().unique(), df["arrival_rate"].sort_values().unique(), ls="--", color="#777777", label="Demand line")
    ax.set_title(f"{name}: throughput sensitivity to arrival rate", fontweight="bold")
    ax.set_xlabel("Arrival rate (items/hour)")
    ax.set_ylabel("Throughput (items/hour)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_cost_benefit(name, cost_df, out_path):
    df = cost_df.copy()
    size = 100 + df["payback_months"].replace(0, 0.5).clip(upper=12) * 80
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(df["additional_cost_hr"], df["throughput_improvement_hr"], s=size, color="#4c78a8", alpha=0.75)
    for _, row in df.iterrows():
        ax.annotate(
            f"{row['config']}\nRs.{row['net_benefit_hr']:.0f}/hr",
            (row["additional_cost_hr"], row["throughput_improvement_hr"]),
            xytext=(8, 5),
            textcoords="offset points",
        )
    ax.set_title(f"{name}: cost-benefit of redesign options", fontweight="bold")
    ax.set_xlabel("Additional operating cost (Rs./hour)")
    ax.set_ylabel("Throughput improvement (items/hour)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_cycle_kde(name, base_steps, best_steps, arrival_rate, out_path):
    base = run_simulation(SimConfig(base_steps, arrival_rate, seed=901))
    best = run_simulation(SimConfig(best_steps, arrival_rate, seed=901))
    base_cycle = np.array(base.total_cycle_times) * 60
    best_cycle = np.array(best.total_cycle_times) * 60
    fig, ax = plt.subplots(figsize=(8, 5))
    for values, label, color in [
        (base_cycle, "Current State", "#d95f5f"),
        (best_cycle, "Best Redesign", "#2ca25f"),
    ]:
        values = values[np.isfinite(values)]
        xs = np.linspace(values.min(), values.max(), 300)
        density = gaussian_kde(values)(xs)
        ax.plot(xs, density, label=f"{label} (mean {values.mean():.1f} min)", color=color, lw=2)
        ax.fill_between(xs, density, alpha=0.25, color=color)
    ax.set_title(f"{name}: before vs. after cycle time distribution", fontweight="bold")
    ax.set_xlabel("Cycle time (minutes)")
    ax.set_ylabel("Density")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_queue_panels(name, configs, arrival_rate, bottleneck, out_path):
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=False, sharey=False)
    for ax, (label, steps) in zip(axes.ravel(), configs.items()):
        res = run_simulation(SimConfig(steps, arrival_rate, seed=913))
        trace = pd.DataFrame(res.step_queue_lengths[bottleneck], columns=["time_hr", "queue"])
        ax.plot(trace["time_hr"], trace["queue"], color="#4c78a8", lw=1.8)
        ax.set_title(f"{label}: peak {trace['queue'].max():.0f}")
        ax.set_xlabel("Time (hr)")
        ax.set_ylabel("Queue")
    fig.suptitle(f"{name}: {bottleneck} queue stability comparison", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def validate_erlang_c_against_sim(steps, arrival_rate, scenario_name):
    res = run_replications(SimConfig(steps, arrival_rate, seed=1100), 10)
    rows = []
    for step, params in steps.items():
        if params.get("dist") != "exponential":
            continue
        lam = params.get("lambda", arrival_rate)
        rho = lam / (params["servers"] * params["mu"])
        if rho >= 0.95:
            continue
        _, wq = erlang_c(lam, params["mu"], params["servers"])
        analytical = wq * 60
        simulated = res["wait_times_min"][step][0]
        denom = max(analytical, 0.01)
        rows.append(
            {
                "scenario": scenario_name,
                "step": step,
                "analytical_wait_min": analytical,
                "simulated_wait_min": simulated,
                "abs_pct_error": abs(simulated - analytical) / denom * 100,
            }
        )
    return pd.DataFrame(rows)


def make_notebook(path, title, scenario_key):
    spec = scenario_artifacts(scenario_key)
    prefix = spec["prefix"]
    plot_files = [
        f"outputs/{prefix}_plot_01_process_flow.png",
        f"outputs/{prefix}_plot_02_queue_growth.png",
        f"outputs/{prefix}_plot_03_cycle_time_comparison.png",
        f"outputs/{prefix}_plot_04_wait_breakdown.png",
        f"outputs/{prefix}_plot_05_throughput_violin.png",
        f"outputs/{prefix}_plot_06_mu_sensitivity.png",
        f"outputs/{prefix}_plot_07_arrival_sensitivity.png",
        f"outputs/{prefix}_plot_08_cost_benefit.png",
    ]
    if scenario_key == "warehouse":
        plot_files.extend(
            [
                "outputs/warehouse_plot_09_cycle_time_kde.png",
                "outputs/warehouse_plot_10_queue_panels.png",
            ]
        )
    image_source = []
    for plot_path in plot_files:
        image_source.extend(
            [
                f"display(Markdown('### {Path(plot_path).stem.replace('_', ' ').title()}'))\n",
                f"display(Image(filename='{plot_path}'))\n",
            ]
        )

    cells = [
        {
            "id": f"{scenario_key}-title",
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# {title}\n",
                "\n",
                "This notebook presents the scenario as an operations case study: analytical bottleneck diagnosis, "
                "simulation validation, redesign comparison, stress testing, sensitivity analysis, and cost recommendation.\n",
            ],
        },
        {
            "id": f"{scenario_key}-model-design",
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Modeling Design\n",
                "\n",
                "- Six-step serial process with finite-capacity resources.\n",
                "- Poisson arrivals with exponential inter-arrival times.\n",
                "- Service-time distributions vary by station: exponential, Erlang-2, or lognormal.\n",
                "- First 150 items are discarded as warmup to reduce transient bias.\n",
                "- Each configuration uses 10 replications with reproducible seeds.\n",
                "- All reported confidence intervals are 95% Student's t intervals.\n",
            ],
        },
        {
            "id": f"{scenario_key}-run",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "from IPython.display import Image, Markdown, display\n",
                "from run_analysis import analyse_process, run_all, scenario_artifacts\n",
                "\n",
                f"artifacts = run_all(selected='{scenario_key}')\n",
                f"scenario = artifacts['{scenario_key}']\n",
                f"spec = scenario_artifacts('{scenario_key}')\n",
                "comparison, cost, stress = artifacts['summary_tables']\n",
                "best = scenario['best_label']\n",
            ],
        },
        {
            "id": f"{scenario_key}-analytical-md",
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Analytical Bottleneck Check\n",
                "\n",
                "The first pass uses station utilisation and Erlang-C queueing estimates before simulation. "
                "That makes the bottleneck diagnosis explainable rather than purely empirical.\n",
            ],
        },
        {
            "id": f"{scenario_key}-analytical-code",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "analysis = analyse_process(spec['configs']['Current State']).copy()\n",
                "analysis['Utilisation_rho'] = analysis['Utilisation_rho'].round(3)\n",
                "analysis['Avg_Wait_Time_min'] = analysis['Avg_Wait_Time_min'].replace(float('inf'), pd.NA)\n",
                "display(analysis[['Step', 'Lambda_in', 'Mu_per_server', 'Servers', 'Utilisation_rho', 'Avg_Wait_Time_min', 'Is_Bottleneck']])\n",
            ],
        },
        {
            "id": f"{scenario_key}-results-md",
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Simulation Results\n",
                "\n",
                "The table below compares the current state and redesigns using replicated simulation outputs. "
                "Cycle-time and throughput estimates include 95% confidence intervals.\n",
            ],
        },
        {
            "id": f"{scenario_key}-results-code",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "cols = ['config', 'bottleneck_rho', 'cycle_time_min_mean', 'cycle_time_min_ci_low', 'cycle_time_min_ci_high', 'throughput_hr_mean', 'bottleneck_queue_mean']\n",
                "display(comparison[cols].round(2))\n",
                "display(Markdown(f'**Recommended redesign:** {best}'))\n",
            ],
        },
        {
            "id": f"{scenario_key}-cost-md",
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Cost And Stress Testing\n",
                "\n",
                "Redesigns are evaluated as business decisions, not just queueing improvements. "
                "The cost table converts throughput gains into net benefit, while the stress test checks behavior at +50% demand.\n",
            ],
        },
        {
            "id": f"{scenario_key}-cost-code",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display(cost.round(2))\n",
                "display(stress.round(2))\n",
            ],
        },
        {
            "id": f"{scenario_key}-plots-md",
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Visual Evidence\n",
                "\n",
                "These plots are regenerated from the same simulation pipeline and saved under `outputs/`.\n",
            ],
        },
        {
            "id": f"{scenario_key}-plots-code",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": image_source,
        },
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")


def scenario_artifacts(scenario):
    if scenario == "kyc":
        return {
            "name": "Fintech KYC Verification Pipeline",
            "prefix": "kyc",
            "base_arrival": 120,
            "bottleneck": "Manual Review",
            "configs": {
                "Current State": KYC_STEPS_BASE,
                "Add 2 Agents": KYC_REDESIGN_A,
                "ML Triage": KYC_REDESIGN_B,
                "Triage + 1 Agent": KYC_REDESIGN_C,
            },
            "cost_fn": kyc_costs,
            "sla": 60,
        }
    return {
        "name": "Warehouse Pick-and-Pack",
        "prefix": "warehouse",
        "base_arrival": 100,
        "bottleneck": "Picking",
        "configs": {
            "Current State": WH_STEPS_BASE,
            "Add 2 Pickers": WH_REDESIGN_A,
            "Zone Picking": WH_REDESIGN_B,
            "Zone + 1 Picker": WH_REDESIGN_C,
        },
        "cost_fn": wh_costs,
        "sla": 45,
    }


def run_scenario(key):
    spec = scenario_artifacts(key)
    configs = spec["configs"]
    results = run_config_set(configs, spec["base_arrival"], spec["bottleneck"], 10)
    cost_df = spec["cost_fn"](results)
    best_label = best_by_net(cost_df)
    stress_configs, stress_results, stress_df = evaluate_stress(configs, spec["base_arrival"], spec["bottleneck"], 10)
    mu_df = run_mu_sensitivity(configs, spec["base_arrival"], spec["bottleneck"], best_label)
    arrival_df = run_arrival_sensitivity(configs, spec["base_arrival"], spec["bottleneck"])

    p = spec["prefix"]
    plot_process_flow(spec["name"], configs["Current State"], OUTPUT_DIR / f"{p}_plot_01_process_flow.png")
    plot_queue_growth(p, spec["name"], configs["Current State"], configs[best_label], spec["base_arrival"], spec["bottleneck"], OUTPUT_DIR / f"{p}_plot_02_queue_growth.png")
    plot_cycle_bars(spec["name"], results, spec["sla"], OUTPUT_DIR / f"{p}_plot_03_cycle_time_comparison.png")
    plot_wait_breakdown(spec["name"], results, "Current State", best_label, OUTPUT_DIR / f"{p}_plot_04_wait_breakdown.png")
    plot_throughput_violin(spec["name"], results, OUTPUT_DIR / f"{p}_plot_05_throughput_violin.png")
    plot_mu_sensitivity(spec["name"], mu_df, OUTPUT_DIR / f"{p}_plot_06_mu_sensitivity.png")
    plot_arrival_sensitivity(spec["name"], arrival_df, OUTPUT_DIR / f"{p}_plot_07_arrival_sensitivity.png")
    plot_cost_benefit(spec["name"], cost_df, OUTPUT_DIR / f"{p}_plot_08_cost_benefit.png")
    if key == "warehouse":
        plot_cycle_kde(spec["name"], configs["Current State"], configs[best_label], spec["base_arrival"], OUTPUT_DIR / f"{p}_plot_09_cycle_time_kde.png")
        plot_queue_panels(spec["name"], configs, spec["base_arrival"], spec["bottleneck"], OUTPUT_DIR / f"{p}_plot_10_queue_panels.png")

    comparison = pd.DataFrame(config_rows(spec["name"], key, configs, results, spec["bottleneck"]))
    stress_df["scenario_key"] = key
    cost_df["scenario_key"] = key
    mu_df["scenario_key"] = key
    arrival_df["scenario_key"] = key
    validation_df = validate_erlang_c_against_sim(configs[best_label], spec["base_arrival"], spec["name"])

    return {
        "spec": spec,
        "results": results,
        "stress_results": stress_results,
        "comparison": comparison,
        "stress": stress_df,
        "cost": cost_df,
        "mu_sensitivity": mu_df,
        "arrival_sensitivity": arrival_df,
        "validation": validation_df,
        "best_label": best_label,
    }


def stable_range(arrival_df):
    stable = arrival_df[~arrival_df["unstable"]].groupby("config")["arrival_multiplier"].max()
    if stable.empty:
        return "none", 0.0
    label = stable.sort_values(ascending=False).index[0]
    return label, stable[label]


def first_unstable_mu(mu_df, label):
    df = mu_df[(mu_df["config"] == label) & (mu_df["unstable"])].sort_values("mu_multiplier")
    if df.empty:
        return "not observed in tested range"
    return f"{df.iloc[0]['mu_multiplier']:.1f}x bottleneck mu"


def write_summary(kyc, wh):
    all_comp = pd.concat([kyc["comparison"], wh["comparison"]], ignore_index=True)
    all_cost = pd.concat([kyc["cost"], wh["cost"]], ignore_index=True)
    all_stress = pd.concat([kyc["stress"], wh["stress"]], ignore_index=True)
    validation = pd.concat([kyc["validation"], wh["validation"]], ignore_index=True)

    all_comp.to_csv(OUTPUT_DIR / "results_comparison.csv", index=False)
    all_cost.to_csv(OUTPUT_DIR / "cost_benefit.csv", index=False)
    all_stress.to_csv(OUTPUT_DIR / "stress_test.csv", index=False)
    validation.to_csv(OUTPUT_DIR / "erlang_c_validation.csv", index=False)
    kyc["mu_sensitivity"].to_csv(OUTPUT_DIR / "kyc_mu_sensitivity.csv", index=False)
    wh["mu_sensitivity"].to_csv(OUTPUT_DIR / "warehouse_mu_sensitivity.csv", index=False)
    kyc["arrival_sensitivity"].to_csv(OUTPUT_DIR / "kyc_arrival_sensitivity.csv", index=False)
    wh["arrival_sensitivity"].to_csv(OUTPUT_DIR / "warehouse_arrival_sensitivity.csv", index=False)

    def section(artifact):
        spec = artifact["spec"]
        comp = artifact["comparison"]
        cost = artifact["cost"]
        stress = artifact["stress"]
        best = artifact["best_label"]
        base_row = comp[comp["config"] == "Current State"].iloc[0]
        best_row = comp[comp["config"] == best].iloc[0]
        best_cost = cost[cost["config"] == best].iloc[0]
        bottleneck_rho = base_row["bottleneck_rho"]
        ct_reduction = (base_row["cycle_time_min_mean"] - best_row["cycle_time_min_mean"]) / base_row["cycle_time_min_mean"] * 100
        tp_increase = (best_row["throughput_hr_mean"] - base_row["throughput_hr_mean"]) / base_row["throughput_hr_mean"] * 100
        stress_best = stress[stress["config"] == best].iloc[0]
        stress_status = "collapsed" if stress_best["collapsed"] else "did not meet the collapse rule"
        wide_label, wide_mult = stable_range(artifact["arrival_sensitivity"])
        return (
            f"## {spec['name']}\n"
            f"- Analytical bottleneck: {spec['bottleneck']} with rho={bottleneck_rho:.2f}; "
            f"theoretical capacity is {base_row['capacity_per_hr']:.1f} items/hr and pure processing time is {base_row['theoretical_process_time_min']:.2f} min.\n"
            f"- Current simulation: cycle time {base_row['cycle_time_min_mean']:.1f} min "
            f"(95% CI {base_row['cycle_time_min_ci_low']:.1f}-{base_row['cycle_time_min_ci_high']:.1f}), "
            f"throughput {base_row['throughput_hr_mean']:.1f}/hr "
            f"(95% CI {base_row['throughput_hr_ci_low']:.1f}-{base_row['throughput_hr_ci_high']:.1f}).\n"
            f"- Best redesign by net benefit: {best}. It reduced cycle time by {ct_reduction:.1f}% "
            f"and changed throughput by {tp_increase:.1f}% versus current state.\n"
            f"- Cost recommendation: {best} produces Rs.{best_cost['net_benefit_hr']:.0f}/hr net benefit "
            f"with payback of {best_cost['payback_months']:.2f} months.\n"
            f"- Stress test at +50% demand: {best} {stress_status} "
            f"(average bottleneck queue {stress_best['bottleneck_queue']:.1f}, cycle time {stress_best['cycle_time_min']:.1f} min).\n"
            f"- Sensitivity: {best} becomes unstable at {first_unstable_mu(artifact['mu_sensitivity'], best)}; "
            f"{wide_label} has the widest stable tested demand range up to {wide_mult:.1f}x base demand.\n"
        )

    kyc_base = kyc["comparison"][kyc["comparison"]["config"] == "Current State"].iloc[0]
    kyc_best = kyc["comparison"][kyc["comparison"]["config"] == kyc["best_label"]].iloc[0]
    wh_base = wh["comparison"][wh["comparison"]["config"] == "Current State"].iloc[0]
    wh_best = wh["comparison"][wh["comparison"]["config"] == wh["best_label"]].iloc[0]
    kyc_reduction = (kyc_base["cycle_time_min_mean"] - kyc_best["cycle_time_min_mean"]) / kyc_base["cycle_time_min_mean"] * 100
    wh_tp_inc = (wh_best["throughput_hr_mean"] - wh_base["throughput_hr_mean"]) / wh_base["throughput_hr_mean"] * 100
    wh_cost = wh["cost"].set_index("config")
    wh_payback_ratio = max(0.01, wh_cost.loc["Add 2 Pickers", "payback_months"] or 0.01) / max(0.01, wh_cost.loc[wh["best_label"], "payback_months"] or 0.01)
    max_base_peak = 0
    for artifact in [kyc, wh]:
        base_res = artifact["results"]["Current State"]["raw_results"][0]
        step = artifact["spec"]["bottleneck"]
        max_base_peak = max(max_base_peak, max(q for _, q in base_res.step_queue_lengths[step]))
    kyc_range_label, kyc_range = stable_range(kyc["arrival_sensitivity"])
    wh_base_unstable = wh["arrival_sensitivity"][(wh["arrival_sensitivity"]["config"] == "Current State") & (wh["arrival_sensitivity"]["unstable"])]
    base_threshold = wh_base_unstable["arrival_multiplier"].min() if not wh_base_unstable.empty else 1.5

    bullets = [
        f'Modeled fintech KYC pipeline via DES; identified Manual Review bottleneck (rho={kyc_base["bottleneck_rho"]:.2f}); best redesign cut cycle time {kyc_reduction:.0f}% at zero added headcount.',
        f"Simulated warehouse pick-and-pack; {wh['best_label']} improved throughput {wh_tp_inc:.0f}% with Rs.{wh_cost.loc[wh['best_label'], 'net_benefit_hr']:.0f}/hr net benefit.",
        f"Validated redesigns under 50% demand surge; base queues diverged to {max_base_peak:.0f}+ items, exposing concrete surge-capacity limits.",
        f"Sensitivity analysis showed {kyc_range_label} stable up to {kyc_range:.0%} of base demand; warehouse base unstable beyond {base_threshold:.0%}.",
    ]

    kyc_cost = kyc["cost"].set_index("config").loc[kyc["best_label"]]
    wh_best_cost = wh["cost"].set_index("config").loc[wh["best_label"]]
    executive_table = (
        "| Scenario | Bottleneck | Current Cycle Time | Recommended Redesign | Cycle-Time Reduction | Net Benefit |\n"
        "|---|---:|---:|---|---:|---:|\n"
        f"| Fintech KYC | {kyc['spec']['bottleneck']}, rho={kyc_base['bottleneck_rho']:.2f} | "
        f"{kyc_base['cycle_time_min_mean']:.1f} min | {kyc['best_label']} | {kyc_reduction:.1f}% | Rs.{kyc_cost['net_benefit_hr']:.0f}/hr |\n"
        f"| Warehouse | {wh['spec']['bottleneck']}, rho={wh_base['bottleneck_rho']:.2f} | "
        f"{wh_base['cycle_time_min_mean']:.1f} min | {wh['best_label']} | "
        f"{((wh_base['cycle_time_min_mean'] - wh_best['cycle_time_min_mean']) / wh_base['cycle_time_min_mean'] * 100):.1f}% | "
        f"Rs.{wh_best_cost['net_benefit_hr']:.0f}/hr |\n"
    )

    summary = (
        "# Process Bottleneck Analysis\n\n"
        "## Executive Recommendation\n"
        + executive_table
        + "\n"
        "Both current-state systems have structural bottlenecks with utilisation above 1.0. "
        "The recommended interventions are selected by net business benefit after simulation, not by capacity gain alone.\n\n"
        + section(kyc)
        + "\n"
        + section(wh)
        + "\n## Erlang-C Validation\n"
        + f"Stable exponential steps in the recommended redesigns had mean absolute wait-time error of {validation['abs_pct_error'].mean():.1f}% versus Erlang-C analytical estimates.\n"
        + "\n## Deliverables\n"
        + "- 2 executable scenario notebooks\n"
        + "- 18 generated plots\n"
        + "- CSV outputs for comparison, cost-benefit, stress testing, sensitivity analysis, and Erlang-C validation\n"
        + "- Reusable SimPy framework with warmup removal, queue monitoring, route fractions, and replication logic\n"
        + "\n## Resume Bullets\n"
        + "\n".join(f"- {bullet}" for bullet in bullets)
        + "\n"
    )
    (PROJECT_DIR / "summary.md").write_text(summary, encoding="utf-8")
    return all_comp, all_cost, all_stress


def run_all(selected=None):
    artifacts = {}
    if selected in (None, "kyc"):
        artifacts["kyc"] = run_scenario("kyc")
    if selected in (None, "warehouse"):
        artifacts["warehouse"] = run_scenario("warehouse")
    if selected is None:
        comp, cost, stress = write_summary(artifacts["kyc"], artifacts["warehouse"])
        make_notebook(PROJECT_DIR / "scenario_a_kyc.ipynb", "Scenario A: Fintech KYC Verification Pipeline", "kyc")
        make_notebook(PROJECT_DIR / "scenario_b_warehouse.ipynb", "Scenario B: Warehouse Pick-and-Pack", "warehouse")
        artifacts["summary_tables"] = (comp, cost, stress)
    else:
        artifacts["summary_tables"] = (artifacts[selected]["comparison"], artifacts[selected]["cost"], artifacts[selected]["stress"])
    return artifacts


if __name__ == "__main__":
    run_all()
    print(f"Analysis complete. Outputs written to {OUTPUT_DIR}")
