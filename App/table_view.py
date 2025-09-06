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
# search_text = st.text_input("Movie title", "sales")
# st.write("The current movie title is", search_text)

@st.cache_data(ttl=30)  # only re-query if it's been 30 seconds
def getData():
    # This example query depends on the nyctaxi data set in Unity Catalog, see https://docs.databricks.com/en/discover/databricks-datasets.html for details
    return sqlQuery("""SELECT * FROM workspace.trustmodel.trust_scores""")

def getColumnData():
    return sqlQuery("SELECT table_schema, table_name, column_name, CASE WHEN comment IS NULL THEN 0 ELSE 1 END as comment FROM information_schema.columns")

data = getData()
column_data = getColumnData()




# Convert to numeric, coerce errors (non-numeric -> NaN), then fill NaN with 0
data['trust_score'] = pd.to_numeric(data['trust_score'], errors='coerce').fillna(0).astype(int)
# values = st.slider("Select a range of values", 0.0, 100.0, (0.0, 75.0))
# d = data[(data['tag_value'] >= values[0]) & (data['tag_value'] <= values[1])]


# d = data[(data['trust_score'].astype(int) >= values[0]) & 
#          (data['trust_score'].astype(int) <= values[1])]

d=data

col1, col2, col3 = st.columns([1, 0.5, 0.5], gap="small")
with col1:
    event = st.dataframe(data=d[["catalogName", "schemaName", "tableName", "trust_score"]], column_config={
            "catalogName": "Catalog",
            "schemaName": "Schema",
            "tableName": "Table",
            "trust_score": st.column_config.ProgressColumn(
                "Trust Score",
                help="The Trust Score on a scale of 0-100",
                format="%f",
                min_value=0,
                max_value=100,
            ),
        }, height=600
        ,use_container_width=False
        ,on_select="rerun"
        ,selection_mode=["single-row"]
        )



with col2:
    if event.selection.rows:

        selected = event.selection.rows  # This is a list of the selected row indices
        filtered_df = d.iloc[selected]

        filtered_columns = column_data[(column_data['table_name'] == filtered_df['tableName'].iloc[0]) &
                                    (column_data['table_schema'] == filtered_df['schemaName'].iloc[0])]

        # a, b = st.columns(2)
        # c, d = st.columns(2)
        st.subheader(filtered_df['tableName'].iloc[0], divider="gray")
         # col1, col2, col3 = st.columns(3)
        if filtered_df['trust_score'].iloc[0] < 50:
            st.badge("Low Trust Score", icon=":material/warning:", color="red")
        elif filtered_df['trust_score'].iloc[0] < 80:
            st.badge("Medium Trust Score", icon=":material/info:", color="yellow")
        else:
            st.badge("High Trust Score", icon=":material/check:", color="green")
        st.metric("Table Has Comments", "✅" if filtered_df['hasComments'].iloc[0] == True else "❌",border=True)
        st.metric("All Columns Have Comments", "✅" if filtered_df['allColumnsHaveComments'].iloc[0] == True else "❌",chart_data=filtered_columns['comment'], chart_type="area", border=True)
        st.metric("Has Human Owner", "✅" if filtered_df['hasHumanOwner'].iloc[0] == True else "❌", border=True)
        st.metric(label="Weeks In Production", value=filtered_df['weeksInProduction'], border=True)
# from numpy.random import default_rng as rng
# changes = list(rng(4).standard_normal(20))
# data = [sum(changes[:i]) for i in range(20)]
# delta = round(data[-1], 2)

# row = st.container(horizontal=True)
# with row:
#     st.metric(
#         "Line", 10, delta, "off",None, "hidden", False, "stretch", "content", data, "line"
#     )
