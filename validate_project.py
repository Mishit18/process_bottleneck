import json
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "outputs"


REQUIRED_ROOT_FILES = [
    "README.md",
    "summary.md",
    "requirements.txt",
    "pyproject.toml",
    "LICENSE",
    "simulation_framework.py",
    "run_analysis.py",
    "validate_project.py",
    "scenario_a_kyc.ipynb",
    "scenario_b_warehouse.ipynb",
]

REQUIRED_OUTPUTS = [
    "results_comparison.csv",
    "cost_benefit.csv",
    "stress_test.csv",
    "erlang_c_validation.csv",
    "kyc_arrival_sensitivity.csv",
    "kyc_mu_sensitivity.csv",
    "warehouse_arrival_sensitivity.csv",
    "warehouse_mu_sensitivity.csv",
]

REQUIRED_PLOTS = [
    "kyc_plot_01_process_flow.png",
    "kyc_plot_02_queue_growth.png",
    "kyc_plot_03_cycle_time_comparison.png",
    "kyc_plot_04_wait_breakdown.png",
    "kyc_plot_05_throughput_violin.png",
    "kyc_plot_06_mu_sensitivity.png",
    "kyc_plot_07_arrival_sensitivity.png",
    "kyc_plot_08_cost_benefit.png",
    "warehouse_plot_01_process_flow.png",
    "warehouse_plot_02_queue_growth.png",
    "warehouse_plot_03_cycle_time_comparison.png",
    "warehouse_plot_04_wait_breakdown.png",
    "warehouse_plot_05_throughput_violin.png",
    "warehouse_plot_06_mu_sensitivity.png",
    "warehouse_plot_07_arrival_sensitivity.png",
    "warehouse_plot_08_cost_benefit.png",
    "warehouse_plot_09_cycle_time_kde.png",
    "warehouse_plot_10_queue_panels.png",
]


def assert_exists(paths):
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise AssertionError("Missing required files:\n" + "\n".join(missing))


def assert_not_empty(paths):
    empty = [str(path) for path in paths if path.stat().st_size == 0]
    if empty:
        raise AssertionError("Empty generated files:\n" + "\n".join(empty))


def validate_notebooks():
    for name in ["scenario_a_kyc.ipynb", "scenario_b_warehouse.ipynb"]:
        notebook = json.loads((PROJECT_DIR / name).read_text(encoding="utf-8"))
        if notebook.get("nbformat") != 4:
            raise AssertionError(f"{name} is not a nbformat v4 notebook")
        if len(notebook.get("cells", [])) < 8:
            raise AssertionError(f"{name} should contain narrative and result cells")
        missing_ids = [i for i, cell in enumerate(notebook["cells"]) if "id" not in cell]
        if missing_ids:
            raise AssertionError(f"{name} has cells without ids: {missing_ids}")


def validate_outputs():
    comparison = pd.read_csv(OUTPUT_DIR / "results_comparison.csv")
    cost = pd.read_csv(OUTPUT_DIR / "cost_benefit.csv")
    stress = pd.read_csv(OUTPUT_DIR / "stress_test.csv")
    validation = pd.read_csv(OUTPUT_DIR / "erlang_c_validation.csv")

    if comparison.shape[0] != 8:
        raise AssertionError("results_comparison.csv should contain 8 rows")
    if cost.shape[0] != 6:
        raise AssertionError("cost_benefit.csv should contain 6 redesign rows")
    if stress.shape[0] != 8:
        raise AssertionError("stress_test.csv should contain 8 stress-test rows")

    if comparison["cycle_time_min_mean"].isna().any():
        raise AssertionError("Cycle-time means contain null values")
    if comparison["throughput_hr_mean"].isna().any():
        raise AssertionError("Throughput means contain null values")
    if validation["abs_pct_error"].mean() > 10.5:
        raise AssertionError("Erlang-C validation error exceeds tolerance")


def validate_text_quality():
    combined = "\n".join(
        [
            (PROJECT_DIR / "README.md").read_text(encoding="utf-8"),
            (PROJECT_DIR / "summary.md").read_text(encoding="utf-8"),
            (PROJECT_DIR / "docs" / "methodology.md").read_text(encoding="utf-8"),
            (PROJECT_DIR / "docs" / "portfolio_case_study.md").read_text(encoding="utf-8"),
            (PROJECT_DIR / "docs" / "interview_guide.md").read_text(encoding="utf-8"),
        ]
    )
    banned = ["TODO", "TBD", "[X]", "[Y]", "[Z]", "placeholder"]
    found = [token for token in banned if token.lower() in combined.lower()]
    if found:
        raise AssertionError(f"Unresolved placeholder text found: {found}")


def validate_repo_controls():
    workflow = PROJECT_DIR / ".github" / "workflows" / "validation.yml"
    tests = PROJECT_DIR / "tests" / "test_simulation_framework.py"
    assert_exists([workflow, tests])
    assert_not_empty([workflow, tests])

    workflow_text = workflow.read_text(encoding="utf-8")
    for command in ["pytest", "python validate_project.py"]:
        if command not in workflow_text:
            raise AssertionError(f"GitHub workflow does not run: {command}")


def main():
    root_files = [PROJECT_DIR / name for name in REQUIRED_ROOT_FILES]
    output_files = [OUTPUT_DIR / name for name in REQUIRED_OUTPUTS]
    plot_files = [OUTPUT_DIR / name for name in REQUIRED_PLOTS]
    doc_files = [
        PROJECT_DIR / "docs" / "methodology.md",
        PROJECT_DIR / "docs" / "portfolio_case_study.md",
        PROJECT_DIR / "docs" / "interview_guide.md",
    ]

    assert_exists(root_files + output_files + plot_files + doc_files)
    assert_not_empty(root_files + output_files + plot_files + doc_files)
    validate_notebooks()
    validate_outputs()
    validate_text_quality()
    validate_repo_controls()

    print("Project validation passed.")
    print(f"Checked {len(root_files)} root files, {len(output_files)} CSV outputs, and {len(plot_files)} plots.")


if __name__ == "__main__":
    main()
