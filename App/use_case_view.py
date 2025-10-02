import os
from databricks import sql
from databricks.sdk.core import Config
import streamlit as st
import pandas as pd
import numpy as np

# Ensure environment variable is set correctly
assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

def sqlQuery(query: str) -> pd.DataFrame:
    cfg = Config() # Pull environment variables for auth
    # print (f"cfg: {cfg}")
    # print (f"DATABRICKS_WAREHOUSE_ID: {os.getenv('DATABRICKS_WAREHOUSE_ID')}")
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
        credentials_provider=lambda: cfg.authenticate
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

st.set_page_config(layout="wide")

@st.cache_data(ttl=30)  # only re-query if it's been 30 seconds.
def getData(qry):
    return sqlQuery(qry)

def getMetricData(qry):
    return sqlQuery(qry)

# =========================
# Config
# =========================
TRUST_SCORES_TABLE = "workspace.trustmodel.trust_scores" 
# Add usersWithAccess and users28d columns for demo purposes
# In a real scenario, these would come from actual usage logs or access control systems
q = f"SELECT *, CAST(RAND()*(1000-100)+100 AS INT) AS usersWithAccess, CAST(RAND()*(250-10)+10 AS INT) AS users28d FROM {TRUST_SCORES_TABLE}"
data = getData(q)


st.header("Trust Score Demo")

# =========================
# Utilities
# =========================
def safe_cols(df_or_table_cols, wanted):
    return [c for c in wanted if c in df_or_table_cols]

def as_bool(v):
    if isinstance(v, bool): return v
    if v is None or (isinstance(v, float) and np.isnan(v)): return None
    if isinstance(v, (int, np.integer)): return bool(v)
    if isinstance(v, str): return v.strip().lower() in ("true", "1", "yes", "y")
    return None

def check(v):
    if v is None: return "—"
    return "✅" if v else "❌"

def build_fqn(row):
    parts = []
    for c in ["catalogName","schemaName","tableName"]:
        if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
            parts.append(str(row[c]))
    if parts:
        return ".".join(parts)
    # Fallbacks
    if "schemaName" in row.index and "tableName" in row.index:
        return f"{row['schemaName']}.{row['tableName']}"
    return row.get("tableName","<unknown>")

@st.cache_data(show_spinner=False)
def load_scores():
    # Discover columns first to avoid SELECT errors
    available = data.columns
    wanted = [
        "catalogName","schemaName","tableName","trust_score",
        "hasComments","hasMarkdownDescription","allColumnsHaveComments","hasHumanOwner",
        "dqChecks","slaDefined",
        "weeksInProduction","usersWithAccess","users28d",
        # feel free to add more metrics over time
    ]
    cols = safe_cols(available, wanted)
    q = f"SELECT {', '.join(cols)} FROM {TRUST_SCORES_TABLE}"
    pdf = data

    # Normalize types & compute convenience columns
    boolish = ["hasComments","hasMarkdownDescription","allColumnsHaveComments","hasHumanOwner","dqChecks","slaDefined"]
    for c in boolish:
        if c in pdf.columns:
            pdf[c] = pdf[c].map(as_bool)

    if "trust_score" in pdf.columns:
        pdf["trust_score"] = pd.to_numeric(pdf["trust_score"], errors="coerce").fillna(0).astype(int)

    for c in ["weeksInProduction","usersWithAccess","users28d"]:
        if c in pdf.columns:
            pdf[c] = pd.to_numeric(pdf[c], errors="coerce")

    pdf["fqn"] = pdf.apply(build_fqn, axis=1)
    # Nice default ordering
    sort_cols = ["trust_score","users28d","weeksInProduction"]
    sort_cols = [c for c in sort_cols if c in pdf.columns]
    pdf = pdf.sort_values(sort_cols, ascending=[False] + [False]*(len(sort_cols)-1)).reset_index(drop=True)
    return pdf

def scorecard(row):
    # Left: details table; Right: big score
    left, right = st.columns([3,1])
    with left:
        st.subheader("Data Governance Score")
        details = []

        if "hasComments" in row.index:             details.append(("Table comments",           check(row["hasComments"])))      
        if "hasMarkdownDescription" in row.index:   details.append(("Markdown description",     check(row["hasMarkdownDescription"])))
        if "allColumnsHaveComments" in row.index:   details.append(("Column comments",          check(row["allColumnsHaveComments"])))
        if "hasHumanOwner" in row.index:            details.append(("👤 Human owner",          check(row["hasHumanOwner"])))
        if "dqChecks" in row.index:                 details.append(("DQ checks",                check(row["dqChecks"])))
        if "slaDefined" in row.index:               details.append(("SLA defined",              check(row["slaDefined"])))
        if "weeksInProduction" in row.index:        details.append(("Age in weeks",             int(row["weeksInProduction"]) if pd.notna(row["weeksInProduction"]) else "—"))
        if "usersWithAccess" in row.index:          details.append((r"\# humans with access",     int(row["usersWithAccess"]) if pd.notna(row["usersWithAccess"]) else "—"))
        if "users28d" in row.index:                 details.append((r"\# users (28d)",            int(row["users28d"]) if pd.notna(row["users28d"]) else "—"))
        
        st.table(pd.DataFrame(details, columns=["Score details","Value"]).astype(str))

    with right:
        st.metric("Score", int(row.get("trust_score", 0)))

def list_numeric_columns(fqn):
    try:
        dtypes = data.dtypes
        numeric_prefixes = ("int","bigint","double","float","decimal","smallint","tinyint","long","short")
        return [c for c,t in dtypes if any(t.startswith(p) for p in numeric_prefixes)]
    except Exception:
        return []

def run_metric(fqn, agg, col=None):
    if agg == "row_count":
        sql = f"SELECT COUNT(*) AS value FROM {fqn}"
    else:
        sql = f"SELECT {agg.upper()}({col}) AS value FROM {fqn}"
    try:
        d = getMetricData(sql)
        return float(d["value"])
    except Exception as e:
        st.warning(f"Query failed: {e}")
        return None

def pct_true(series):
    if series is None or len(series)==0: return 0.0
    s = series.dropna()
    if len(s)==0: return 0.0
    return float((s==True).mean()*100)

# =========================
# Data
# =========================
scores = load_scores()
if scores.empty:
    st.stop()

# =========================
# Header
# =========================
st.title("AdventureWorks Data Trust Demo")

top = st.container()
with top:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Tables", len(scores))
    with c2:
        st.metric("Avg trust score", int(scores["trust_score"].mean()) if "trust_score" in scores.columns else "—")
    with c3:
        st.metric("% with table comments", f"{pct_true(scores.get('hasComments')):0.0f}%")
    with c4:
        st.metric("% with human owner", f"{pct_true(scores.get('hasHumanOwner')):0.0f}%")

st.divider()

# =========================
# Tabs
# =========================

TAB_NAMES = ["📚 Catalog", "🚧 Trust Gate", "⚖️ Compare", "🛠️ Fix-it Backlog", "📊 Executive"]

# Persist selection across reruns
_default = st.session_state.get("active_tab", TAB_NAMES[0])
active_tab = st.radio(
    "Navigate",
    TAB_NAMES,
    index=TAB_NAMES.index(_default),
    horizontal=True,
    key="active_tab",
)
st.divider()

# ---------- Catalog ----------
if active_tab == "📚 Catalog":
    q = st.text_input("Search (schema/table)", "")
    min_score = st.slider("Min trust score", 0, 100, 0)
    filtered = scores[scores["trust_score"] >= min_score]
    if q.strip():
        filtered = filtered[filtered["fqn"].str.contains(q, case=False, na=False)]

    left, right = st.columns([2, 1], vertical_alignment="top")

    with left:
        display_cols = ["fqn","trust_score"]
        for c in ["hasComments","hasMarkdownDescription","allColumnsHaveComments","hasHumanOwner","weeksInProduction","users28d"]:
            if c in filtered.columns: display_cols.append(c)

        df_show = filtered[display_cols].copy()
        for c in ["hasComments","hasMarkdownDescription","allColumnsHaveComments","hasHumanOwner"]:
            if c in df_show.columns:
                df_show[c] = df_show[c].map(check)
        st.dataframe(df_show, hide_index=True, use_container_width=True)
        
    with right:
        st.subheader("Scorecard")
        options = filtered["fqn"].tolist()
        
        
        if not options:
            st.info("No tables match the filters.")
        else:
            sel = st.selectbox("Table / View", options=options)
            row = filtered.loc[filtered["fqn"]==sel].iloc[0]
            scorecard(row)
    
    
# ---------- Trust Gate ----------
elif active_tab == "🚧 Trust Gate":
    st.write("Block queries against low-trust tables.")
    enforce = st.toggle("Enforce gate", True)
    gate_min = st.slider("Minimum trust score to allow", 0, 100, 80)

    sel = st.selectbox("Pick a table to query", options=scores["fqn"].tolist())
    row = scores.loc[scores["fqn"]==sel].iloc[0]
    st.caption(f"Selected score: **{int(row.get('trust_score',0))}**")

    # Metric to run
    numeric_cols = list_numeric_columns(sel)
    agg = st.selectbox("Aggregation", ["row_count"] + (["sum","avg"] if numeric_cols else []))
    metric_col = None
    if agg in ("sum","avg"):
        metric_col = st.selectbox("Numeric column", options=numeric_cols)

    # Gate logic
    if enforce and int(row.get("trust_score",0)) < gate_min:
        st.error(f"Blocked: {sel} has trust score {int(row.get('trust_score',0))} < {gate_min}")
    else:
        val = run_metric(sel, agg, metric_col)
        if val is not None:
            st.success(f"{agg.upper()} result: {val:,.2f}" if agg!="row_count" else f"Row count: {int(val):,}")

    with st.expander("Show example SQL"):
        if agg == "row_count":
            st.code(f"SELECT COUNT(*) FROM {sel};", language="sql")
        else:
            st.code(f"SELECT {agg.upper()}({metric_col}) FROM {sel};", language="sql")

# ---------- Compare ----------
elif active_tab == "⚖️ Compare":
    st.write("Compare the same calculation across two sources (e.g., high- vs low-trust).")
    left, right = st.columns(2)

    # Defaults: best and worst tables by score
    default_hi = scores.iloc[0]["fqn"]
    default_lo = scores.iloc[-1]["fqn"]

    hi = left.selectbox("Table A (usually higher trust)", options=scores["fqn"].tolist(), index=scores["fqn"].tolist().index(default_hi))
    lo = right.selectbox("Table B (usually lower trust)", options=scores["fqn"].tolist(), index=scores["fqn"].tolist().index(default_lo))

    agg_choice = st.selectbox("Aggregation", ["row_count","sum","avg"])
    # Intersect numeric cols for both tables if needed
    common_numeric = set(list_numeric_columns(hi)).intersection(set(list_numeric_columns(lo)))
    if agg_choice in ("sum","avg"):
        if not common_numeric:
            st.warning("No common numeric columns—falling back to row count.")
            agg_choice = "row_count"
            col_choice = None
        else:
            col_choice = st.selectbox("Numeric column (common to both)", options=sorted(common_numeric))
    else:
        col_choice = None

    a = run_metric(hi, agg_choice, col_choice)
    b = run_metric(lo, agg_choice, col_choice)

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("A value", f"{a:,.2f}" if a is not None and agg_choice!="row_count" else (f"{int(a):,}" if a is not None else "—"), delta=None)
    with c2: st.metric("B value", f"{b:,.2f}" if b is not None and agg_choice!="row_count" else (f"{int(b):,}" if b is not None else "—"), delta=None)
    with c3:
        if a is not None and b is not None:
            st.metric("Difference (A - B)", f"{(a-b):,.2f}" if agg_choice!="row_count" else f"{int(a-b):,}")

    with st.expander("Scores & details"):
        for fqn in [hi, lo]:
            r = scores.loc[scores["fqn"]==fqn].iloc[0]
            st.markdown(f"**{fqn}** — score **{int(r.get('trust_score',0))}**")
            scorecard(r)

# ---------- Fix-it Backlog ----------
elif active_tab == "🛠️ Fix-it Backlog":
    st.write("Find and export specific fixes (missing comments, owners, etc.).")
    needs = []
    if "hasComments" in scores.columns:             needs.append(("Missing table comments", ~scores["hasComments"].fillna(False)))
    if "allColumnsHaveComments" in scores.columns:  needs.append(("Missing column comments", ~scores["allColumnsHaveComments"].fillna(False)))
    if "hasHumanOwner" in scores.columns:           needs.append(("No human owner", ~scores["hasHumanOwner"].fillna(False)))
    if "hasMarkdownDescription" in scores.columns:  needs.append(("No markdown description", ~scores["hasMarkdownDescription"].fillna(False)))


    if not needs:
        st.info("No boolean quality fields found.")
    else:
        filters = st.multiselect("Show tables that have any of:", [n for n,_ in needs], default=[n for n,_ in needs])
        mask = np.zeros(len(scores), dtype=bool)
        for label, cond in needs:
            if label in filters:
                mask |= cond.values
        backlog = scores[mask].copy()

        # Rank by impact if usage exists
        if "users28d" in backlog.columns:
            backlog = backlog.sort_values(["users28d","trust_score"], ascending=[False, True])

        show_cols = ["fqn","trust_score"]
        for c in ["hasComments","hasMarkdownDescription","allColumnsHaveComments","hasHumanOwner","weeksInProduction","users28d"]:
            if c in backlog.columns: show_cols.append(c)

        pretty = backlog[show_cols].copy()
        for c in ["hasComments","hasMarkdownDescription","allColumnsHaveComments","hasHumanOwner"]:
            if c in pretty.columns: pretty[c] = pretty[c].map(check)
        st.dataframe(pretty, hide_index=True, use_container_width=True)

        # Downloadable CSV backlog with actionable description
        if len(backlog):
            dl = backlog.copy()
            def mk_action(r):
                missing = []
                if "hasComments" in r.index and not as_bool(r["hasComments"]): missing.append("Add table comment")
                if "hasMarkdownDescription" in r.index and not as_bool(r["hasMarkdownDescription"]): missing.append("Add markdown description")
                if "allColumnsHaveComments" in r.index and not as_bool(r["allColumnsHaveComments"]): missing.append("Add column comments")
                if "hasHumanOwner" in r.index and not as_bool(r["hasHumanOwner"]): missing.append("Assign human owner")
                return "; ".join(missing) if missing else "—"
            dl["recommended_action"] = dl.apply(mk_action, axis=1)
            st.download_button("Download backlog CSV", dl.to_csv(index=False).encode("utf-8"), file_name="trust_backlog.csv", mime="text/csv")

            with st.expander("Example ticket text for selected items"):
                pick = st.multiselect("Tables", options=dl["fqn"].tolist(), default=dl["fqn"].head(3).tolist())
                for fqn in pick:
                    r = dl.loc[dl["fqn"]==fqn].iloc[0]
                    actions = r["recommended_action"]
                    st.code(
f"""Title: Improve data trust for {fqn}
Summary: Trust score = {int(r.get('trust_score',0))}. Recommended actions: {actions}.
Details:
- Table comments: {check(r.get('hasComments'))}
- Markdown description: {check(r.get('hasMarkdownDescription'))}
- Column comments: {check(r.get('allColumnsHaveComments'))}
- Human owner: {check(r.get('hasHumanOwner'))}
- Age (weeks): {int(r.get('weeksInProduction')) if pd.notna(r.get('weeksInProduction')) else '—'}
- Users (28d): {int(r.get('users28d')) if pd.notna(r.get('users28d')) else '—'}
""", language="markdown")

# ---------- Executive ----------
else:  # "📊 Executive"
    st.write("High-level view of trust posture and risk.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Average score", int(scores["trust_score"].mean()) if "trust_score" in scores.columns else "—")
    with c2:
        st.metric("% with column comments", f"{pct_true(scores.get('allColumnsHaveComments')):0.0f}%")
    with c3:
        st.metric("% with markdown description", f"{pct_true(scores.get('hasMarkdownDescription')):0.0f}%")

    st.subheader("Top risky & popular")
    if "users28d" in scores.columns:
        top_risk = (scores.sort_values(["trust_score","users28d"], ascending=[True, False])
                           .head(10))[["fqn","trust_score","users28d"]]
        st.dataframe(top_risk, hide_index=True, use_container_width=True)
    else:
        st.info("No users28d metric available to rank by popularity.")

    st.subheader("Score distribution")
    st.bar_chart(data=scores,y="trust_score", x="tableName")
