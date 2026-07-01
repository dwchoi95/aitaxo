import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/aitaxo_mpl")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parent
FIG_DIR = ROOT / "figs"

INK = "#111111"
MUTED = "#555555"
ARROW = "#333333"
BLUE = "#dcecf8"
BLUE_D = "#4f7fa7"
ORANGE = "#fde6d2"
ORANGE_D = "#b96a31"
GREEN = "#ddf1e9"
GREEN_D = "#348767"
GOLD = "#f4ecd0"
GOLD_D = "#837232"
PURPLE = "#ece1f5"
PURPLE_D = "#7554a3"
RED = "#f7dddd"
RED_D = "#a84f4f"
OLIVE = "#eaf0d6"
OLIVE_D = "#718536"


def text(ax, x, y, s, fs=6.2, bold=False, color=INK, ha="center", va="center"):
    ax.text(
        x,
        y,
        s,
        fontsize=fs,
        fontweight="bold" if bold else "normal",
        color=color,
        ha=ha,
        va=va,
        linespacing=1.05,
    )


def panel(ax, x, y, w, h, title):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.006,rounding_size=0.010",
            linewidth=1.1,
            edgecolor=INK,
            facecolor="white",
        )
    )
    text(ax, x + w - 0.020, y + 0.030, title, fs=8.8, bold=True, ha="right")


def dash_box(ax, x, y, w, h):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.004,rounding_size=0.006",
            linewidth=0.8,
            edgecolor="#666666",
            facecolor="none",
            linestyle=(0, (4, 3)),
        )
    )


def small_box(ax, x, y, w, h, label, fc, ec, fs=5.5, bold=False, dashed=False):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.003,rounding_size=0.005",
            linewidth=0.8,
            edgecolor=ec,
            facecolor=fc,
            linestyle="--" if dashed else "-",
        )
    )
    text(ax, x + w / 2, y + h / 2, label, fs=fs, bold=bold)


def arrow(ax, a, b, rad=0.0, lw=1.0, color=ARROW, scale=8.0):
    ax.add_patch(
        FancyArrowPatch(
            a,
            b,
            arrowstyle="-|>",
            mutation_scale=scale,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=3,
            shrinkB=3,
        )
    )


def database(ax, cx, cy, w, h, fc=BLUE, ec=BLUE_D):
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor=fc, edgecolor=ec, linewidth=1.0))
    ax.add_patch(Ellipse((cx, cy + h / 2), w, h * 0.25, facecolor=fc, edgecolor=ec, linewidth=1.0))
    ax.add_patch(Ellipse((cx, cy), w, h * 0.25, facecolor="none", edgecolor=ec, linewidth=0.8))
    ax.add_patch(Ellipse((cx, cy - h / 2), w, h * 0.25, facecolor=fc, edgecolor=ec, linewidth=1.0))


def funnel(ax, cx, cy, w, h):
    pts = [
        (cx - w / 2, cy + h / 2),
        (cx + w / 2, cy + h / 2),
        (cx + w * 0.18, cy + h * 0.02),
        (cx + w * 0.09, cy - h / 2),
        (cx - w * 0.09, cy - h / 2),
        (cx - w * 0.18, cy + h * 0.02),
    ]
    ax.add_patch(Polygon(pts, closed=True, facecolor="white", edgecolor=BLUE_D, linewidth=1.0))


def code_stack(ax, x, y, w, h, n, fc, ec):
    for i in range(n):
        dx = i * w * 0.15
        dy = i * h * 0.12
        ax.add_patch(Rectangle((x + dx, y + dy), w, h, facecolor=fc, edgecolor=ec, linewidth=0.8))
        text(ax, x + dx + w / 2, y + dy + h / 2, "</>", fs=4.8, bold=True, color=ec)


def people(ax, x, y, s, colors):
    for i, c in enumerate(colors):
        cx = x + i * s * 0.78
        ax.add_patch(Circle((cx, y + s * 0.23), s * 0.17, facecolor="white", edgecolor=c, linewidth=1.0))
        ax.add_patch(
            FancyBboxPatch(
                (cx - s * 0.24, y - s * 0.22),
                s * 0.48,
                s * 0.30,
                boxstyle="round,pad=0.002,rounding_size=0.012",
                facecolor="white",
                edgecolor=c,
                linewidth=1.0,
            )
        )


def chip(ax, cx, cy, w, h, fc=GREEN, ec=GREEN_D):
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor=fc, edgecolor=ec, linewidth=1.0))
    for i in range(4):
        yy = cy - h * 0.36 + i * h * 0.24
        ax.plot([cx - w * 0.64, cx - w / 2], [yy, yy], color=ec, lw=0.7)
        ax.plot([cx + w / 2, cx + w * 0.64], [yy, yy], color=ec, lw=0.7)
    ax.add_patch(Circle((cx, cy), min(w, h) * 0.18, facecolor="white", edgecolor=ec, linewidth=0.7))


def judge(ax, cx, cy, w, h):
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor="white", edgecolor=GOLD_D, linewidth=1.0))
    ax.plot([cx - w * 0.28, cx - w * 0.08], [cy, cy - h * 0.20], color=GREEN_D, lw=1.35)
    ax.plot([cx - w * 0.08, cx + w * 0.30], [cy - h * 0.20, cy + h * 0.25], color=GREEN_D, lw=1.35)
    ax.plot([cx - w * 0.32, cx + w * 0.32], [cy - h * 0.33, cy - h * 0.33], color=GOLD_D, lw=0.8)


def verdicts(ax, x, y):
    small_box(ax, x, y, 0.057, 0.075, "AC\nWA/RE\nTLE/CE", "#ffffff", "#888888", fs=4.7, bold=True)


def taxonomy_grid(ax, x, y, s):
    for r in range(3):
        for c in range(4):
            ax.add_patch(
                FancyBboxPatch(
                    (x + c * s * 0.34, y - r * s * 0.34),
                    s * 0.23,
                    s * 0.23,
                    boxstyle="round,pad=0.002,rounding_size=0.004",
                    facecolor="#ffffff",
                    edgecolor=PURPLE_D,
                    linewidth=0.8,
                )
            )


def chat(ax, cx, cy, w, h):
    ax.add_patch(
        FancyBboxPatch(
            (cx - w / 2, cy - h / 2),
            w,
            h,
            boxstyle="round,pad=0.004,rounding_size=0.009",
            facecolor="white",
            edgecolor=OLIVE_D,
            linewidth=0.9,
        )
    )
    ax.add_patch(
        Polygon(
            [(cx - w * 0.15, cy - h / 2), (cx - w * 0.02, cy - h * 0.66), (cx + w * 0.04, cy - h / 2)],
            closed=True,
            facecolor="white",
            edgecolor=OLIVE_D,
            linewidth=0.9,
        )
    )
    ax.plot([cx - w * 0.28, cx + w * 0.24], [cy + h * 0.17, cy + h * 0.17], color=OLIVE_D, lw=0.8)
    ax.plot([cx - w * 0.28, cx + w * 0.10], [cy - h * 0.08, cy - h * 0.08], color=OLIVE_D, lw=0.8)


def bars(ax, x, y, w, h):
    cols = [BLUE_D, ORANGE_D, GREEN_D, PURPLE_D]
    heights = [0.45, 0.75, 0.56, 0.88]
    for i, ht in enumerate(heights):
        bw = w / 6
        ax.add_patch(Rectangle((x + i * bw * 1.35, y), bw, h * ht, facecolor=cols[i], edgecolor="none"))
    ax.plot([x - 0.005, x + w], [y, y], color=INK, lw=0.8)


def build():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.25, 3.15))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    panel(ax, 0.010, 0.130, 0.455, 0.810, "Corpus construction")
    panel(ax, 0.485, 0.605, 0.350, 0.335, "Taxonomy + labeling")
    panel(ax, 0.485, 0.130, 0.350, 0.395, "Reflection diagnostic")
    panel(ax, 0.865, 0.130, 0.125, 0.810, "Analysis")

    # Step 1: problems and filtering
    dash_box(ax, 0.030, 0.575, 0.145, 0.255)
    database(ax, 0.070, 0.725, 0.047, 0.095)
    funnel(ax, 0.135, 0.725, 0.048, 0.095)
    arrow(ax, (0.093, 0.725), (0.111, 0.725))
    small_box(ax, 0.055, 0.600, 0.095, 0.047, "107", BLUE, BLUE_D, fs=6.1, bold=True)
    text(ax, 0.070, 0.675, "Problems", fs=5.4)
    text(ax, 0.135, 0.675, "Filter", fs=5.4)
    text(ax, 0.102, 0.535, "Step 1\ncollect/filter", fs=5.6)

    # Step 2: AI and human submissions
    dash_box(ax, 0.200, 0.575, 0.088, 0.255)
    chip(ax, 0.244, 0.735, 0.040, 0.055)
    code_stack(ax, 0.226, 0.642, 0.024, 0.042, 4, GREEN, GREEN_D)
    text(ax, 0.244, 0.610, "AI bugs", fs=5.4)
    text(ax, 0.244, 0.535, "Step 2a\nAI", fs=5.6)

    dash_box(ax, 0.315, 0.575, 0.105, 0.255)
    people(ax, 0.350, 0.730, 0.043, [ORANGE_D])
    code_stack(ax, 0.355, 0.642, 0.024, 0.042, 3, ORANGE, ORANGE_D)
    text(ax, 0.370, 0.610, "Human bugs", fs=5.4)
    text(ax, 0.368, 0.535, "Step 2b\nhuman", fs=5.6)

    # Step 3: sandbox
    dash_box(ax, 0.155, 0.245, 0.185, 0.180)
    judge(ax, 0.217, 0.335, 0.062, 0.080)
    verdicts(ax, 0.276, 0.322)
    text(ax, 0.217, 0.285, "Sandbox", fs=5.5)
    text(ax, 0.248, 0.210, "Step 3\njudge", fs=5.6)
    arrow(ax, (0.175, 0.630), (0.210, 0.425), rad=-0.08)
    arrow(ax, (0.288, 0.662), (0.255, 0.425), rad=0.05)
    arrow(ax, (0.342, 0.662), (0.280, 0.425), rad=0.08)

    # Step 4: taxonomy and labeling
    dash_box(ax, 0.502, 0.775, 0.088, 0.105)
    people(ax, 0.528, 0.832, 0.036, [PURPLE_D, PURPLE_D])
    text(ax, 0.545, 0.735, "Gold", fs=5.4)
    small_box(ax, 0.612, 0.805, 0.150, 0.040, "Adopt Wei taxonomy", PURPLE, PURPLE_D, fs=5.4, bold=True)
    small_box(ax, 0.612, 0.728, 0.150, 0.040, "Audit LLM judge", PURPLE, PURPLE_D, fs=5.4, bold=True)
    taxonomy_grid(ax, 0.780, 0.862, 0.072)
    text(ax, 0.787, 0.712, "GE/AE labels", fs=5.4)
    arrow(ax, (0.590, 0.827), (0.612, 0.825))
    arrow(ax, (0.762, 0.823), (0.790, 0.825), color=RED_D)
    arrow(ax, (0.762, 0.748), (0.790, 0.780), color=RED_D)
    text(ax, 0.660, 0.665, "Step 4: blind labeling", fs=5.7)

    # Step 5: reflection diagnostic
    code_stack(ax, 0.510, 0.375, 0.027, 0.050, 4, GREEN, GREEN_D)
    text(ax, 0.530, 0.320, "Not-AC", fs=5.4)
    chat(ax, 0.615, 0.385, 0.065, 0.055)
    text(ax, 0.615, 0.320, "Feedback", fs=5.4)
    judge(ax, 0.730, 0.385, 0.055, 0.075)
    text(ax, 0.730, 0.320, "Re-judge", fs=5.4)
    small_box(ax, 0.755, 0.435, 0.042, 0.028, "AC", GREEN, "#888888", fs=4.5, bold=True)
    small_box(ax, 0.755, 0.240, 0.042, 0.028, "NAC", RED, "#888888", fs=4.5, bold=True)
    arrow(ax, (0.540, 0.385), (0.578, 0.385))
    arrow(ax, (0.650, 0.385), (0.695, 0.385))
    arrow(ax, (0.730, 0.423), (0.758, 0.448))
    arrow(ax, (0.730, 0.346), (0.758, 0.255))
    text(ax, 0.655, 0.205, "Step 5: self-reflection", fs=5.7)

    # Step 6: analysis
    database(ax, 0.905, 0.750, 0.040, 0.085, RED, RED_D)
    text(ax, 0.905, 0.670, "Labeled\ncorpus", fs=5.2)
    bars(ax, 0.913, 0.470, 0.052, 0.140)
    text(ax, 0.940, 0.390, "RQ1-RQ4", fs=6.1, bold=True)
    small_box(ax, 0.885, 0.235, 0.078, 0.045, "AI vs Human", RED, RED_D, fs=5.3, bold=True)
    text(ax, 0.925, 0.198, "Step 6: compare", fs=5.5)
    arrow(ax, (0.815, 0.750), (0.885, 0.750))
    arrow(ax, (0.797, 0.385), (0.885, 0.735), rad=-0.20)
    arrow(ax, (0.905, 0.705), (0.935, 0.600))
    arrow(ax, (0.940, 0.470), (0.925, 0.280))

    # Cross-panel links
    arrow(ax, (0.420, 0.700), (0.485, 0.800), rad=-0.10, lw=1.2)
    arrow(ax, (0.340, 0.335), (0.485, 0.380), rad=0.02, lw=1.2)
    arrow(ax, (0.675, 0.605), (0.675, 0.525), lw=1.0, color=RED_D)

    for ext in ("pdf", "svg"):
        fig.savefig(FIG_DIR / f"overview.{ext}", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


if __name__ == "__main__":
    build()
