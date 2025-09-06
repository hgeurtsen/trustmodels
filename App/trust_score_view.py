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

@st.cache_data(ttl=30)  # only re-query if it's been 30 seconds
def getData():
    # This example query depends on the nyctaxi data set in Unity Catalog, see https://docs.databricks.com/en/discover/databricks-datasets.html for details
    return sqlQuery("""SELECT * FROM workspace.trustmodel.trust_scores""")

data = getData()

st.header("Trust Score Demo")


# Convert to numeric, coerce errors (non-numeric -> NaN), then fill NaN with 0
data['trust_score'] = pd.to_numeric(data['trust_score'], errors='coerce').fillna(0).astype(int)
values = st.slider("Select a range of values", 0.0, 100.0, (0.0, 75.0))
# d = data[(data['tag_value'] >= values[0]) & (data['tag_value'] <= values[1])]

tab1, tab2 = st.tabs(["📈 Chart", "🗃 Data"])



d = data[(data['trust_score'].astype(int) >= values[0]) & 
         (data['trust_score'].astype(int) <= values[1])]

col1, col2 = st.columns([3, 1])
with col1:
    tab1.bar_chart(data=d, height=400, width=700, y="trust_score", x="tableName")
#with col2:
    #st.subheader("Filter Score")
    # fromdate = st.text_input("From (OrderDate)", value="2022-01-01")
    # todate = st.text_input("To (OrderDate)", value="2022-05-01")
    # d = data[(data['pickup_zip'] == int(pickup)) & (data['dropoff_zip'] == int(dropoff))]
    # st.write(f"# **${d['SalesAmount'].mean() if len(d) > 0 else 99:.2f}**")

event = tab2.dataframe(data=d, column_config={
        "trust_score": st.column_config.ProgressColumn(
            "Trust Score",
            help="The Trust Score on a scale of 0-100",
            format="%f",
            min_value=0,
            max_value=100,
        ),
    }, height=600
    , use_container_width=False
    #,on_select="rerun"
    #,selection_mode=["single-row"]
    )

# selected = event.selection.rows  # This is a list of the selected row indices
# selected
# filtered_df = d.iloc[selected]


# st.dataframe(data=filtered_df, column_config={
#         "trust_score": st.column_config.ProgressColumn(
#             "Trust Score",
#             help="The Trust Score on a scale of 0-100",
#             format="%f",
#             min_value=0,
#             max_value=100,
#         ),
#     }, height=600
#     , use_container_width=False
#     ,on_select="rerun"
#     ,selection_mode=["single-row"])