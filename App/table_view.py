import os
from databricks import sql
from databricks.sdk.core import Config
import streamlit as st
import pandas as pd

# Ensure environment variable is set correctly
assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

def sqlQuery(query: str) -> pd.DataFrame:
    cfg = Config() # Pull environment variables for auth
    print (f"cfg: {cfg}")
    print (f"DATABRICKS_WAREHOUSE_ID: {os.getenv('DATABRICKS_WAREHOUSE_ID')}")
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/aebf760781cefe19",
        credentials_provider=lambda: cfg.authenticate
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

st.set_page_config(layout="wide")
st.header("Trust Score Demo")

@st.cache_data(ttl=30)  # only re-query if it's been 30 seconds
def getData():
    # This example query depends on the nyctaxi data set in Unity Catalog, see https://docs.databricks.com/en/discover/databricks-datasets.html for details
    return sqlQuery("""SELECT * FROM workspace.trustmodel.trust_scores""")

data = getData()

df=data

# Build a friendly FQN for a selector
df["fqn"] = df["catalogName"].fillna("") + "." + df["schemaName"].fillna("") + "." + df["tableName"].fillna("")
df = df.sort_values(["catalogName","schemaName","tableName"])

# --- UI: pick a table/view ---
selection = st.selectbox("Table / View", options=df["fqn"].tolist())
row = df.loc[df["fqn"] == selection].iloc[0]  # selected row as a Series

# --- helpers ---
def checkmark(v):
    if pd.isna(v): return "—"
    return "✅" if bool(v) else "❌"

def exists(col):
    return col in row.index

# If your column means “has a *human* owner”, keep the label as “Human owner”.
# If you actually track “non-human owner”, flip the boolean or rename the label below.
owner_label = "👤 Human owner" if "hasHumanOwner" in row.index else "🤖 Non-human owner"

# --- assemble the details table (only show what exists) ---
details = []

# Comments
if exists("hasComments"):             details.append(("Table comments",  checkmark(row["hasComments"])))
if exists("allColumnsHaveComments"):  details.append(("Column comments", checkmark(row["allColumnsHaveComments"])))

# Ownership
if exists("hasHumanOwner"):           details.append((owner_label,       checkmark(row["hasHumanOwner"])))

# Quality / process
if exists("dqChecks"):                details.append(("DQ checks",       checkmark(row["dqChecks"])))
if exists("slaDefined"):              details.append(("SLA defined",     checkmark(row["slaDefined"])))

# Age / usage
if exists("weeksInProduction"):       details.append(("Age in weeks",    int(row["weeksInProduction"]) if pd.notna(row["weeksInProduction"]) else "—"))
if exists("usersWithAccess"):         details.append(("# humans with access", int(row["usersWithAccess"]) if pd.notna(row["usersWithAccess"]) else "—"))
if exists("users28d"):                details.append(("# users (28d)",   int(row["users28d"]) if pd.notna(row["users28d"]) else "—"))

details_df = pd.DataFrame(details, columns=["Score details", "Value"])

# --- layout to match your mock ---
left, right = st.columns([3,1])

with left:
    st.subheader("Data Governance Score")
    st.dataframe(
        details_df,
        hide_index=True,
        use_container_width=True
    )

with right:
    st.write("")  # a little top padding
    big_score = int(row["trust_score"]) if pd.notna(row["trust_score"]) else 0
    st.metric(label="Score", value=big_score)

# (Optional) show where the numbers came from for transparency
with st.expander("Raw row"):
    st.json(row.to_dict())