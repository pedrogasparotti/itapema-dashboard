#!/usr/bin/env python3
"""Exploratory analysis + plots over the Itapema building-permits dataset.

Reads relatorio_planejamento_itapema.csv (from extract_report.py) and produces four
figures in plots/:
  01_timeseries.png    total requests & total m² per year (two stacked panels)
  02_histograms.png    m² distribution across four equal-count year windows
  03_owner_ranking.png top-20 owners by total m² and by permit count
  04_concentration.png land-concentration trend (Gini, top-10% share, HHI) over years

Time axis = year from the process number (NNN/YYYY). Owner identity = requerente code
(the leading number), which is stable where the source name is truncated.

Run:  python3 analyze_report.py
Deps: pandas, numpy, matplotlib
"""

import os
import re

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(SCRIPT_DIR, "relatorio_planejamento_itapema.csv")
PLOTS = os.path.join(SCRIPT_DIR, "plots")

# --- validated palette (dataviz skill reference, light surface #fcfcfb) ---
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"       # categorical slot 1 / sequential base
GREEN = "#008300"      # categorical slot 2
ORANGE = "#eb6834"     # categorical slot 6
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"]  # light->dark


def style():
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": BASELINE,
        "axes.linewidth": 0.8,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def parse_m2(s):
    """Brazilian-formatted metragem -> float. '3.566,25 M²' -> 3566.25 ; '' -> NaN."""
    s = str(s)
    m = re.search(r"([\d.]+,\d+)", s)      # 3.566,25
    if m:
        return float(m.group(1).replace(".", "").replace(",", "."))
    m = re.search(r"\d+", s)               # bare integer fallback
    return float(m.group(0)) if m else np.nan


def load():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
    df["ano"] = df["processo"].str.extract(r"/(\d{4})")[0].astype(int)
    df["m2"] = df["metragem"].apply(parse_m2)
    df["owner_code"] = df["requerente"].str.extract(r"^(\d+)\s*-")[0]
    df["owner_name"] = df["requerente"].apply(lambda s: re.sub(r"^\d+\s*-\s*", "", s).strip())

    def label(row):
        name = row["owner_name"] or "(sem nome)"
        return f"{row['owner_code']} — {name}" if row["owner_code"] else name
    df["owner_label"] = df.apply(label, axis=1)
    return df


def save(fig, name):
    os.makedirs(PLOTS, exist_ok=True)
    path = os.path.join(PLOTS, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  wrote {path}")


# --- concentration metrics ---
def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    n = x.size
    if n == 0 or x.sum() == 0:
        return np.nan
    idx = np.arange(1, n + 1)
    return float((np.sum((2 * idx - n - 1) * x)) / (n * x.sum()))


def top_decile_share(x):
    x = np.sort(np.asarray(x, dtype=float))[::-1]
    n = x.size
    if n == 0 or x.sum() == 0:
        return np.nan
    k = max(1, int(np.ceil(n * 0.10)))
    return float(x[:k].sum() / x.sum())


def hhi(x):
    x = np.asarray(x, dtype=float)
    if x.sum() == 0:
        return np.nan
    shares = x / x.sum()
    return float(np.sum(shares ** 2))       # 1/N (diverse) -> 1 (monopoly)


def plot_timeseries(df):
    import matplotlib.pyplot as plt
    per_year = df.groupby("ano").agg(n=("processo", "size"),
                                     total_m2=("m2", "sum")).reset_index()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True)

    ax1.bar(per_year["ano"], per_year["n"], color=BLUE, width=0.75)
    ax1.set_ylabel("Nº de processos")
    ax1.set_title("Processos de alvará por ano (1994–2026)", loc="left")
    peak = per_year.loc[per_year["n"].idxmax()]
    ax1.annotate(f"{int(peak.n)} em {int(peak.ano)}",
                 xy=(peak.ano, peak.n), xytext=(0, 6), textcoords="offset points",
                 ha="center", color=INK2, fontsize=9)

    ax2.bar(per_year["ano"], per_year["total_m2"] / 1000, color=GREEN, width=0.75)
    ax2.set_ylabel("Área total (mil m²)")
    ax2.set_xlabel("Ano do processo")
    ax2.set_title("Área total requerida por ano", loc="left")
    pk2 = per_year.loc[per_year["total_m2"].idxmax()]
    ax2.annotate(f"{pk2.total_m2/1000:,.0f} mil m² em {int(pk2.ano)}",
                 xy=(pk2.ano, pk2.total_m2/1000), xytext=(0, 6),
                 textcoords="offset points", ha="center", color=INK2, fontsize=9)

    fig.text(0.01, -0.01, "Obs.: 2026 é ano parcial.", color=MUTED, fontsize=8)
    fig.tight_layout()
    save(fig, "01_timeseries.png")
    plt.close(fig)
    return per_year


def plot_histograms(df):
    import matplotlib.pyplot as plt
    d = df[df["m2"] > 0].copy()
    # equal-count quartile windows over the year axis
    d["win"] = pd.qcut(d["ano"], 4)
    wins = sorted(d["win"].unique(), key=lambda iv: iv.left)

    # shared log-spaced bins so shapes compare directly
    lo, hi = d["m2"].min(), d["m2"].max()
    bins = np.logspace(np.log10(lo), np.log10(hi), 30)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    per_win = {}
    for ax, iv in zip(axes.ravel(), wins):
        sub = d[d["win"] == iv]
        y0, y1 = int(np.ceil(iv.left)) + (1 if iv.left != int(iv.left) else 0), int(iv.right)
        # use actual min/max year in the bucket for an honest label
        span = f"{int(sub['ano'].min())}–{int(sub['ano'].max())}"
        ax.hist(sub["m2"], bins=bins, color=BLUE, edgecolor=SURFACE, linewidth=0.5)
        med = sub["m2"].median()
        ax.axvline(med, color=ORANGE, linewidth=1.6)
        # median value in a fixed corner box, clear of the tallest bars
        ax.annotate(f"mediana {med:,.0f} m²", xy=(0.97, 0.92), xycoords="axes fraction",
                    color=ORANGE, fontsize=8, va="top", ha="right",
                    bbox=dict(boxstyle="round,pad=0.25", fc=SURFACE, ec=GRID, lw=0.6))
        ax.set_title(f"{span}  (n={len(sub)})", loc="left")
        ax.set_xscale("log")
        per_win[span] = sub["m2"].describe()
    for ax in axes[-1]:
        ax.set_xlabel("Área (m², escala log)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Nº de processos")
    fig.suptitle("Dispersão da área construída por janela temporal (quartis iguais)",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    save(fig, "02_histograms.png")
    plt.close(fig)
    return per_win


def plot_owner_ranking(df):
    import matplotlib.pyplot as plt
    by = df.groupby("owner_code")
    label = by["owner_label"].first()
    m2_rank = by["m2"].sum().sort_values(ascending=False).head(20)
    cnt_rank = by.size().sort_values(ascending=False).head(20)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(14, 8))

    def hbar(ax, series, title, unit, scale=1.0, fmt="{:,.0f}"):
        labels = [label.get(c, c) for c in series.index][::-1]
        vals = series.values[::-1] / scale
        y = np.arange(len(vals))
        ax.barh(y, vals, color=BLUE, height=0.72)
        ax.set_yticks(y)
        ax.set_yticklabels([l[:34] for l in labels], fontsize=8)
        ax.set_title(title, loc="left")
        ax.set_xlabel(unit)
        ax.grid(axis="y", visible=False)
        for yi, v in zip(y, vals):
            ax.annotate(fmt.format(v), xy=(v, yi), xytext=(3, 0),
                        textcoords="offset points", va="center", fontsize=7.5, color=INK2)

    hbar(axL, m2_rank, "Top 20 proprietários por área total", "Área total (mil m²)",
         scale=1000, fmt="{:,.1f}")
    hbar(axR, cnt_rank, "Top 20 proprietários por nº de processos", "Nº de processos")
    fig.suptitle("Ranking de proprietários (agrupados por código do requerente)",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    save(fig, "03_owner_ranking.png")
    plt.close(fig)
    return m2_rank, cnt_rank, label


def plot_concentration(df, min_owners=20):
    import matplotlib.pyplot as plt
    rows = []
    for ano, g in df.groupby("ano"):
        # area metrics: only owners who actually declared area that year, else the
        # decile-share/HHI collapse to trivial extremes in low-area years.
        m2_by_owner = g[g["m2"] > 0].groupby("owner_code")["m2"].sum()
        cnt_by_owner = g.groupby("owner_code").size()
        rows.append({
            "ano": ano,
            "n_owners_area": m2_by_owner.size, "n_owners_cnt": cnt_by_owner.size,
            "gini_m2": gini(m2_by_owner), "top10_m2": top_decile_share(m2_by_owner),
            "hhi_m2": hhi(m2_by_owner),
            "gini_cnt": gini(cnt_by_owner), "top10_cnt": top_decile_share(cnt_by_owner),
            "hhi_cnt": hhi(cnt_by_owner),
        })
    c = pd.DataFrame(rows)
    # require enough owners on BOTH measures so no panel shows a low-sample artifact
    c = c[(c["n_owners_area"] >= min_owners) &
          (c["n_owners_cnt"] >= min_owners)].reset_index(drop=True)

    fig, (axA, axB) = plt.subplots(2, 1, figsize=(11, 8.6), sharex=True)

    def panel(ax, gini_col, top_col, hhi_col, title, legend_loc):
        ax.plot(c["ano"], c[gini_col], color=BLUE, marker="o", ms=4, lw=2, label="Gini")
        ax.plot(c["ano"], c[top_col], color=GREEN, marker="s", ms=4, lw=2,
                label="Participação do decil superior")
        ax.plot(c["ano"], c[hhi_col], color=ORANGE, marker="^", ms=4, lw=2,
                label="HHI (normalizado)")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Índice (0–1)")
        ax.set_title(title, loc="left")
        # direct end-labels
        for col, color in [(gini_col, BLUE), (top_col, GREEN), (hhi_col, ORANGE)]:
            ax.annotate(f"{c[col].iloc[-1]:.2f}", xy=(c['ano'].iloc[-1], c[col].iloc[-1]),
                        xytext=(4, 0), textcoords="offset points", color=color,
                        fontsize=8, va="center")
        # legend inside an empty band of each panel, clear of the title and the lines
        ax.legend(frameon=True, framealpha=0.9, edgecolor=GRID, facecolor=SURFACE,
                  fontsize=8, ncol=1, loc=legend_loc)

    panel(axA, "gini_m2", "top10_m2", "hhi_m2",
          "Concentração da ÁREA por proprietário", "center left")
    panel(axB, "gini_cnt", "top10_cnt", "hhi_cnt",
          "Concentração dos PROCESSOS por proprietário", "upper left")
    axB.set_xlabel("Ano do processo")
    axB.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    axB.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}"))
    fig.suptitle(f"Concentração vs. diversidade da propriedade ao longo dos anos "
                 f"(anos com ≥ {min_owners} proprietários)",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    save(fig, "04_concentration.png")
    plt.close(fig)
    return c


def trend(series):
    """Sign of a simple linear fit over the index -> human word."""
    y = series.dropna().values
    if len(y) < 3:
        return "indefinido"
    slope = np.polyfit(np.arange(len(y)), y, 1)[0]
    if slope > 0.001:
        return "SUBINDO (mais concentração)"
    if slope < -0.001:
        return "CAINDO (mais diversidade)"
    return "ESTÁVEL"


def main():
    if not os.path.exists(CSV):
        raise SystemExit(f"Missing {CSV} — run extract_report.py first.")
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        raise SystemExit("Install matplotlib:  python3 -m pip install matplotlib")

    style()
    df = load()
    print(f"Loaded {len(df)} rows | years {df.ano.min()}–{df.ano.max()} | "
          f"owners {df.owner_code.nunique()} | m²>0 {(df.m2>0).sum()}")

    print("\n[1] time series")
    per_year = plot_timeseries(df)
    print(per_year.tail(6).to_string(index=False))

    print("\n[2] histograms by quartile window")
    per_win = plot_histograms(df)
    for span, desc in per_win.items():
        print(f"  {span}: median={desc['50%']:,.0f}  mean={desc['mean']:,.0f}  "
              f"max={desc['max']:,.0f}  n={int(desc['count'])}")

    print("\n[3] owner ranking (top 5 shown)")
    m2_rank, cnt_rank, label = plot_owner_ranking(df)
    for c, v in m2_rank.head(5).items():
        print(f"  by m²  : {label.get(c, c)[:40]:40} {v:>12,.0f} m²")
    for c, v in cnt_rank.head(5).items():
        print(f"  by cnt : {label.get(c, c)[:40]:40} {v:>4} processos")

    print("\n[4] concentration over time")
    c = plot_concentration(df)
    first, last = c.iloc[0], c.iloc[-1]
    print(f"  span {int(first.ano)}–{int(last.ano)} (years with >= 20 owners)")
    print(f"  Gini area   : {first.gini_m2:.2f} -> {last.gini_m2:.2f}   trend {trend(c.gini_m2)}")
    print(f"  Top10% area : {first.top10_m2:.2f} -> {last.top10_m2:.2f}  trend {trend(c.top10_m2)}")
    print(f"  Gini count  : {first.gini_cnt:.2f} -> {last.gini_cnt:.2f}   trend {trend(c.gini_cnt)}")
    print("\nDone. Figures in plots/.")


if __name__ == "__main__":
    main()
