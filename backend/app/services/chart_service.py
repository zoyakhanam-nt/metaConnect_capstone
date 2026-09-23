import io
from typing import Any

import matplotlib
matplotlib.use("Agg")  

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


class ChartService:
    """Object-Oriented Service for rendering dashboard analytical charts."""

    def __init__(self, theme: str = "whitegrid"):
        self.theme = theme
        sns.set_theme(style=self.theme)

    def _fig_to_png_bytes(self, fig: plt.Figure) -> bytes:
        """Convert a matplotlib Figure to PNG bytes."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    def render_connection_status_chart(self, status_counts: dict[str, int]) -> bytes:
        """Render a pie chart of connections grouped by status."""
        fig, ax = plt.subplots(figsize=(5, 4))
        values = list(status_counts.values())
        if sum(values) == 0:
            ax.text(0.5, 0.5, "No connections yet", ha="center", va="center")
            ax.axis("off")
        else:
            ax.pie(
                values,
                labels=list(status_counts.keys()),
                autopct="%1.0f%%",
                startangle=90,
            )
            ax.axis("equal")
        ax.set_title("Connections by Status")
        return self._fig_to_png_bytes(fig)

    def render_runs_over_time_chart(self, rows: list[dict[str, Any]]) -> bytes:
        """Render a pie chart showing ingestion runs by status."""
        df = pd.DataFrame(rows)
        fig, ax = plt.subplots(figsize=(6, 4))
        if df.empty:
            ax.text(0.5, 0.5, "No ingestion runs yet", ha="center", va="center")
            ax.axis("off")
        else:
            counts = df["status"].value_counts()
            ax.pie(
                counts.values,
                labels=counts.index,
                autopct="%1.0f%%",
                startangle=90,
            )
            ax.set_title("Ingestion Runs (last 14 days)")
            ax.axis("equal")
        return self._fig_to_png_bytes(fig)

    def render_metadata_counts_chart(self, counts: dict[str, int]) -> bytes:
        """Render a pie chart showing the relative metadata volume."""
        fig, ax = plt.subplots(figsize=(5, 4))
        values = list(counts.values())
        if sum(values) == 0:
            ax.text(0.5, 0.5, "No metadata yet", ha="center", va="center")
            ax.axis("off")
        else:
            ax.pie(
                values,
                labels=list(counts.keys()),
                autopct="%1.0f%%",
                startangle=90,
            )
            ax.axis("equal")
        ax.set_title("Metadata Volume")
        return self._fig_to_png_bytes(fig)