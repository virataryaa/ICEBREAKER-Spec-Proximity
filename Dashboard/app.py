import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Spec Proximity", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 70% 60% at 20% 80%, rgba(26,74,90,.50) 0%, transparent 65%),
        radial-gradient(ellipse 60% 50% at 80% 20%, rgba(42,85,104,.45) 0%, transparent 60%),
        radial-gradient(ellipse 80% 70% at 50% 30%, rgba(79,176,200,.10) 0%, transparent 55%),
        #0D1620;
    background-attachment: fixed;
}
[data-testid="stHeader"] {
    background: rgba(13,22,32,.85) !important;
    backdrop-filter: saturate(180%) blur(16px);
    -webkit-backdrop-filter: saturate(180%) blur(16px);
    border-bottom: 1px solid rgba(188,212,222,.14);
}
/* Fix text visibility on dark background */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] strong {
    color: #d4eaf0 !important;
}
[data-testid="stCaptionContainer"] p {
    color: #7ab8c8 !important;
}
label, .stNumberInput label {
    color: #d4eaf0 !important;
}
</style>
""", unsafe_allow_html=True)

DB = Path(__file__).parent.parent / "Database"

# (ticker, display label, COT source, rollex file stem, default proximity k-lots)
COMMODITY_CONFIG = [
    ("KC",  "Arabica",      "cit",    "rollex_KC",  2),
    ("RC",  "Robusta",      "disagg", "rollex_RC",  2),
    ("SB",  "Sugar",        "cit",    "rollex_SB",  5),
    ("CC",  "Cocoa (NYC)",  "cit",    "rollex_CC",  5),
    ("LCC", "Liffe Cocoa",  "disagg", "rollex_LCC", 2),
    ("CT",  "Cotton",       "cit",    "rollex_CT",  5),
]


@st.cache_data(ttl=3600)
def load_cot():
    cit = pd.read_parquet(DB / "cot_cit.parquet")
    disagg = pd.read_parquet(DB / "cot_disagg.parquet")

    cit["net_spec"] = (
        (cit["Spec Long"]    - cit["Spec Short"])    +
        (cit["Index Long"]   - cit["Index Short"])   +
        (cit["Non Rep Long"] - cit["Non Rep Short"])
    )
    disagg["net_spec"] = (
        (disagg["MM Long"]      - disagg["MM Short"])      +
        (disagg["Other Long"]   - disagg["Other Short"])   +
        (disagg["Non Rep Long"] - disagg["Non Rep Short"])
    )
    return cit, disagg


@st.cache_data(ttl=3600)
def load_rollex():
    out = {}
    for ticker, _, _, stem, _ in COMMODITY_CONFIG:
        path = DB / f"{stem}.parquet"
        if path.exists():
            df = pd.read_parquet(path)[["rollex_px"]].copy()
            df.index = pd.to_datetime(df.index)
            out[ticker] = df.sort_index()
    return out


def nearest_price(rollex_df, date):
    if rollex_df is None or rollex_df.empty:
        return None
    i = rollex_df.index.searchsorted(date, side="right") - 1
    return float(rollex_df.iloc[i]["rollex_px"]) if i >= 0 else None


def build_table(cot_df, ticker, rollex_df, k):
    df = cot_df[cot_df["Commodity"] == ticker].sort_values("Date", ascending=False).reset_index(drop=True).copy()
    if df.empty:
        return pd.DataFrame(), None

    current_spec = float(df.iloc[0]["net_spec"])
    threshold    = k * 1000

    # Mark which rows are within proximity
    df["in_prox"] = abs(df["net_spec"] - current_spec) <= threshold

    # For each in-proximity row, find the index of the next in-proximity row
    # (next = further back in time = higher index in descending df)
    prox_idx_list = df.index[df["in_prox"]].tolist()
    next_prox = {
        prox_idx_list[i]: prox_idx_list[i + 1]
        for i in range(len(prox_idx_list) - 1)
    }

    rows = []
    for idx, row in df.iterrows():
        d      = pd.Timestamp(row["Date"])
        spec_d = int(row["net_spec"])
        in_prox = bool(row["in_prox"])

        prev_date_str = ""
        wks_val = px_d = px_p = perf_val = spec_p = np.nan

        if in_prox:
            px_raw = nearest_price(rollex_df, d)
            px_d   = round(px_raw, 2) if px_raw is not None else np.nan

            if idx in next_prox:
                prev_row  = df.loc[next_prox[idx]]
                prev_d    = pd.Timestamp(prev_row["Date"])
                prev_date_str = prev_d.strftime("%d/%m/%Y")
                wks_val   = float(round((d - prev_d).days / 7))
                spec_p    = round(int(prev_row["net_spec"]) / 1000, 1)
                px_p_raw  = nearest_price(rollex_df, prev_d)
                px_p      = round(px_p_raw, 2) if px_p_raw is not None else np.nan
                if px_raw is not None and px_p_raw is not None:
                    perf_val = round((px_raw - px_p_raw) / px_p_raw * 100, 2)

        rows.append({
            "Date":      d.strftime("%d/%m/%Y"),
            "Prev Date": prev_date_str,
            "Wks":       wks_val,
            "Px (D1)":   px_d,
            "Px2":       px_p,
            "Perf %":    perf_val,
            "Spec 1":    round(spec_d / 1000, 1),
            "Spec 2":    spec_p,
        })

    return pd.DataFrame(rows), current_spec


def color_perf(col):
    styles = []
    for v in col:
        if pd.isna(v):
            styles.append("")
        elif v > 0:
            styles.append("background-color:#1a3d1a;color:#4ade80;font-weight:bold")
        elif v < 0:
            styles.append("background-color:#3d1a1a;color:#f87171;font-weight:bold")
        else:
            styles.append("")
    return styles


def render_panel(col, ticker, label, cot_df, rollex_all, default_k):
    with col:
        h = st.columns([3, 2, 1])
        h[0].markdown(f"**{label}**")
        h[1].markdown("**Spec Proximity**")
        k = h[2].number_input(
            "", min_value=1, max_value=100, value=default_k,
            key=f"k_{ticker}", label_visibility="collapsed",
        )

        tbl, curr = build_table(cot_df, ticker, rollex_all.get(ticker), k)
        if tbl.empty:
            st.warning("No data")
            return

        n_matches = int(tbl["Perf %"].notna().sum())
        n_pos     = int((tbl["Perf %"].fillna(0) > 0).sum())
        st.caption(
            f"Current net spec: {curr/1000:.1f}k lots  |  "
            f"{n_matches} hist. matches  |  {n_pos}/{n_matches} positive"
        )

        fmt = {
            "Wks":     lambda x: str(int(x)) if pd.notna(x) else "",
            "Px (D1)": lambda x: f"{x:.2f}"   if pd.notna(x) else "",
            "Px2":     lambda x: f"{x:.2f}"   if pd.notna(x) else "",
            "Perf %":  lambda x: f"{x:+.1f}%" if pd.notna(x) else "",
            "Spec 1":  lambda x: f"{x:.1f}k"  if pd.notna(x) else "",
            "Spec 2":  lambda x: f"{x:.1f}k"  if pd.notna(x) else "",
        }

        styled = tbl.style.format(fmt, na_rep="").apply(color_perf, subset=["Perf %"])
        st.dataframe(styled, hide_index=True, height=420, use_container_width=True)


# ── Layout ────────────────────────────────────────────────────────────────────

st.markdown(
    "<h2 style='text-align:center;margin-bottom:2px;color:#d4eaf0'>Spec Proximity</h2>"
    "<p style='text-align:center;color:#7ab8c8;font-size:13px;margin-top:0'>"
    "NYC: Spec + Index + Non Rep &nbsp;|&nbsp; European: Managed Money + Others Net + Non Rep"
    "</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

cit, disagg = load_cot()
rollex      = load_rollex()
sources     = {"cit": cit, "disagg": disagg}

for batch in [COMMODITY_CONFIG[:3], COMMODITY_CONFIG[3:]]:
    cols = st.columns(3, gap="medium")
    for col, (ticker, label, src_key, _, default_k) in zip(cols, batch):
        render_panel(col, ticker, label, sources[src_key], rollex, default_k)
    st.markdown("")
