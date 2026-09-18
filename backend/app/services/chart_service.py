import io

import matplotlib
matplotlib.use("Agg")  # headless rendering, no display needed inside the container

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")


def _fig_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def render_connection_status_chart(status_counts: dict[str, int]) -> bytes:
    df = pd.DataFrame({"status": list(status_counts.keys()), "count": list(status_counts.values())})
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.barplot(data=df, x="status", y="count", hue="status", legend=False, ax=ax)
    ax.set_title("Connections by Status")
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    return _fig_to_png_bytes(fig)


def render_runs_over_time_chart(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(6, 4))
    if df.empty:
        ax.text(0.5, 0.5, "No ingestion runs yet", ha="center", va="center")
        ax.axis("off")
    else:
        counts = df.groupby(["date", "status"]).size().reset_index(name="count")
        sns.barplot(data=counts, x="date", y="count", hue="status", ax=ax)
        ax.set_title("Ingestion Runs (last 14 days)")
        ax.set_xlabel("")
        ax.set_ylabel("Runs")
        plt.xticks(rotation=45, ha="right")
    return _fig_to_png_bytes(fig)


def render_metadata_counts_chart(counts: dict[str, int]) -> bytes:
    df = pd.DataFrame({"level": list(counts.keys()), "count": list(counts.values())})
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.barplot(data=df, x="level", y="count", hue="level", legend=False, ax=ax)
    ax.set_title("Metadata Volume")
    ax.set_xlabel("")
    ax.set_ylabel("Count")
    return _fig_to_png_bytes(fig)