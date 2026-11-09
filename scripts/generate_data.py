"""Generate a mission and write ground truth, CSV, database rows and a sanity chart."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from app import config, db  # noqa: E402
from app.signals import SIGNALS  # noqa: E402
from app.sim.generator import CREW, Mission, generate_mission  # noqa: E402


def long_table(mission: Mission) -> pd.DataFrame:
    """One row per astronaut, day and signal, without missing readings."""
    rows = [
        (who, day + 1, sig, float(v))
        for who, signals in mission.series.items()
        for sig, values in signals.items()
        for day, v in enumerate(values)
        if v == v
    ]
    return pd.DataFrame(rows, columns=["astronaut", "day", "signal", "value"])


def save_db(mission: Mission, table: pd.DataFrame) -> None:
    rows = [(mission.seed, a, int(d), s, v) for a, d, s, v in table.itertuples(index=False)]
    with db.connect() as con:
        con.execute("DELETE FROM readings WHERE seed = ?", (mission.seed,))
        con.executemany("INSERT INTO readings VALUES (?,?,?,?,?)", rows)


def sanity_chart(mission: Mission, path: Path) -> None:
    """One small chart per signal, one line per astronaut."""
    cols = 5
    rows = -(-len(SIGNALS) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(20, rows * 2.6), constrained_layout=True)
    for ax, sig in zip(axes.flat, SIGNALS, strict=False):
        for who in CREW:
            ax.plot(pd.Series(mission.series[who.id][sig.id]).interpolate().to_numpy(), lw=0.8, label=who.tag)
        ax.set_title(f"{sig.name} ({sig.unit})", fontsize=10)
    for ax in axes.flat[len(SIGNALS):]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=7)
    fig.suptitle(f"Synthetic mission, seed {mission.seed}. Sanity check only.")
    fig.savefig(path, dpi=70)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--days", type=int, default=180)
    args = parser.parse_args()

    mission = generate_mission(args.seed, args.days)
    config.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    (config.SYNTHETIC_DIR / "ground_truth.json").write_text(json.dumps(mission.ground_truth, indent=2))
    table = long_table(mission)
    table.to_csv(config.SYNTHETIC_DIR / f"mission_seed{args.seed}.csv", index=False)
    save_db(mission, table)
    sanity_chart(mission, config.SYNTHETIC_DIR / "sanity.png")
    print(f"Wrote {len(table)} readings for seed {args.seed} to {config.SYNTHETIC_DIR}")


if __name__ == "__main__":
    main()
