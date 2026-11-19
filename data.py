"""Load the refined dataset once and derive the analysis columns."""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from analyze_report import gini, hhi, top_decile_share  # noqa: E402,F401  (re-exported)

CSV = ROOT / "relatorio_planejamento_itapema_refinado.csv"
TOTAL = 5051
ANO_PARCIAL = 2026
# A year with fewer processes (or fewer processes with area, for area charts) than
# this is atypical: one or two records would set the whole yearly value.
N_MIN_ANO = 30

# Coded utilização -> analysis group. Order = fixed categorical slot order.
USO_GRUPOS = ["Unifamiliar", "Unif. coletivo", "Multifamiliar", "Multif. + comercial",
              "Comercial", "Interesse social", "Outros", "Sem informação"]
USO_MAP = {
    "101": "Unifamiliar", "103": "Unif. coletivo", "104": "Multifamiliar",
    "105": "Multif. + comercial", "34": "Multif. + comercial", "33": "Comercial",
    "106": "Interesse social", "107": "Interesse social", "112": "Interesse social",
}
# Vertical (multi-unit) typologies: the verticalization proxy.
VERTICAL = {"Multifamiliar", "Multif. + comercial", "Interesse social"}
# Map colouring: point maps validate only 3 categorical slots, so fold to 3 + gray.
USO_MACRO = {"Unifamiliar": "Unifamiliar", "Unif. coletivo": "Unifamiliar",
             "Multifamiliar": "Multifamiliar", "Multif. + comercial": "Multifamiliar",
             "Interesse social": "Multifamiliar", "Comercial": "Comercial"}

PERIODOS = ["até 2005", "2006-2010", "2011-2013", "2014-2019", "2020-2026"]
PJ_RE = re.compile(r"LTDA|S/A|S\.A\b|INCORPORA|CONSTRU|EMPREEND|EIRELI|HOLDING|SPE\b")
ZONA_RE = re.compile(r"^\s*\d+\s*-\s*(Z.*)$")


def strip_code(value):
    return re.sub(r"^\s*\d+\s*-\s*", "", value or "").strip()


@st.cache_data(show_spinner="Carregando dados…")
def load():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
    df["ano"] = df["ano"].astype(int)
    for col in ("metragem_m2", "latitude", "longitude"):
        df[col] = pd.to_numeric(df[col].replace("", np.nan), errors="coerce")

    df["bairro_nome"] = df["bairro"].map(strip_code).replace("", "(sem bairro)")
    # "MORRETES - ZONA 3" and the three "MEIA PRAIA" codes are the same locality.
    df["bairro_macro"] = df["bairro_nome"].str.replace(r"\s*-\s*ZONA\s*\d+$", "", regex=True)
    df["loteamento_nome"] = df["loteamento"].map(strip_code)

    code = df["utilizacao"].str.extract(r"^(\d+)\s*-")[0]
    df["uso_grupo"] = np.where(df["utilizacao"] == "", "Sem informação",
                               code.map(USO_MAP).fillna("Outros"))
    df["uso_macro"] = df["uso_grupo"].map(USO_MACRO).fillna("Outros / sem informação")
    df["vertical"] = df["uso_grupo"].isin(VERTICAL)

    df["zona"] = df["zoneamento"].str.extract(ZONA_RE)[0].fillna("")
    # Process-level decision; the requerimento "Análise" block is empty from 2017 on.
    df["deferido_bool"] = df["deferido_processo"] == "SIM"
    df["periodo"] = pd.cut(df["ano"], [0, 2005, 2010, 2013, 2019, 2100],
                           labels=PERIODOS).astype(str)

    df["owner_code"] = df["requerente"].str.extract(r"^(\d+)\s*-")[0].fillna("")
    df["owner_name"] = df["requerente"].map(strip_code)
    df["owner_label"] = np.where(df["owner_code"] != "",
                                 df["owner_code"] + " · " + df["owner_name"], df["owner_name"])
    df["tipo_requerente"] = np.where(df["owner_name"].str.upper().str.contains(PJ_RE),
                                     "Pessoa jurídica (heurística)", "Pessoa física / não identificado")
    return df


def apply_filters(df, anos, bairros, usos, so_deferidos):
    m = df["ano"].between(*anos)
    if bairros:
        m &= df["bairro_macro"].isin(bairros)
    m &= df["uso_grupo"].isin(usos)
    if so_deferidos:
        m &= df["deferido_bool"]
    return df[m]


def per_year(df, anos):
    """Aggregate per year, re-indexed over the full selected range (missing years = 0)."""
    g = df.groupby("ano").agg(processos=("processo", "size"),
                              area_m2=("metragem_m2", "sum"),
                              area_media=("metragem_m2", "mean"),
                              area_mediana=("metragem_m2", "median"),
                              com_area=("metragem_m2", "count"),
                              deferidos=("deferido_bool", "sum"))
    g = g.reindex(range(anos[0], anos[1] + 1))
    g[["processos", "area_m2", "com_area", "deferidos"]] = \
        g[["processos", "area_m2", "com_area", "deferidos"]].fillna(0)
    g["taxa_deferimento"] = g["deferidos"] / g["processos"].replace(0, np.nan)
    return g.rename_axis("ano").reset_index()


def area_share(df, mask, by, name):
    """Share of informed area where `mask` holds, per `by` group (groups without area dropped)."""
    tot = df.groupby(by)["metragem_m2"].sum()
    part = df[mask].groupby(by)["metragem_m2"].sum().reindex(tot.index, fill_value=0)
    return (part / tot.where(tot > 0)).dropna().rename(name).rename_axis(by).reset_index()


# --- atypical years ----------------------------------------------------------
def _motivo(row, kind):
    if row["ano"] == ANO_PARCIAL:
        return f"ano parcial ({row['processos']} processos)"
    if row["processos"] == 0:
        return "sem processos"
    if kind == "contagem" or row["processos"] < N_MIN_ANO:
        return f"{row['processos']} processo{'s' if row['processos'] > 1 else ''}"
    return f"{row['com_area']} de {row['processos']} com área"


@st.cache_data
def atypical_years():
    """Every year of the dataset with its coverage and atypical flags.

    Computed on the full dataset (not the filtered one), so the flagged years are a
    property of the source and stay the same under any sidebar filter.
    """
    df = load()
    g = (df.groupby("ano").agg(processos=("processo", "size"), com_area=("metragem_m2", "count"))
           .reindex(range(df["ano"].min(), df["ano"].max() + 1), fill_value=0)
           .rename_axis("ano").reset_index())
    parcial = g["ano"] == ANO_PARCIAL
    g["atip_contagem"] = (g["processos"] < N_MIN_ANO) | parcial
    g["atip_area"] = (g["com_area"] < N_MIN_ANO) | parcial
    for kind in ("contagem", "area"):
        g[f"motivo_{kind}"] = np.where(g[f"atip_{kind}"],
                                      g.apply(_motivo, axis=1, kind=kind), "")
    return g


def atypical_set(kind):
    a = atypical_years()
    return set(a.loc[a[f"atip_{kind}"], "ano"])


def mark_years(frame, kind, ocultar):
    """Add `atipico`/`motivo` to a per-year frame, or drop those years when hiding."""
    a = atypical_years().set_index("ano")
    out = frame.copy()
    out["atipico"] = out["ano"].map(a[f"atip_{kind}"]).fillna(False).astype(bool)
    out["motivo"] = out["ano"].map(a[f"motivo_{kind}"]).fillna("")
    return out[~out["atipico"]] if ocultar else out


def drop_atypical(df, kind, ocultar):
    """Row-level version for period or unordered aggregations."""
    return df[~df["ano"].isin(atypical_set(kind))] if ocultar else df


@st.cache_data
def atypical_periods():
    """Period-level flags for area aggregations ("até 2005" has 1 process with area)."""
    df = load()
    g = df.groupby("periodo").agg(processos=("processo", "size"), com_area=("metragem_m2", "count"))
    g["atipico"] = g["com_area"] < N_MIN_ANO
    g["motivo"] = np.where(g["atipico"], g["com_area"].astype(str) + " de "
                           + g["processos"].astype(str) + " com área", "")
    return g


def mark_periods(frame):
    """Fade periods with too little area data (used when atypical years are shown)."""
    a = atypical_periods()
    out = frame.copy()
    out["atipico"] = out["periodo"].map(a["atipico"]).fillna(False).astype(bool)
    out["motivo"] = out["periodo"].map(a["motivo"]).fillna("")
    return out


def fmt_years(years):
    """{1994,...,2004,2005,2006,2026} -> '1994-2004, 2005, 2006, 2026' (runs of 3+ only)."""
    years, runs = sorted(years), []
    for y in years:
        if runs and y == runs[-1][1] + 1:
            runs[-1][1] = y
        else:
            runs.append([y, y])
    parts = []
    for a, b in runs:
        parts += [f"{a}-{b}"] if b - a >= 2 else [str(y) for y in range(a, b + 1)]
    return ", ".join(parts)


def fmt_int(v):
    return f"{v:,.0f}".replace(",", ".")


def fmt_pct(v):
    return "n/d" if pd.isna(v) else f"{v:.0%}".replace(".", ",")
