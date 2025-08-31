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
    return sqlQuery("""SELECT tbl.table_catalog, tbl.table_schema, tbl.table_name, tag.tag_name, tag.tag_value FROM information_schema.tables tbl   
LEFT JOIN information_schema.table_tags tag
ON tbl.table_catalog = tag.catalog_name
AND tbl.table_schema = tag.schema_name
AND tbl.table_name = tag.table_name
AND tag.tag_name = 'Trust Score'
WHERE tbl.table_type = 'MANAGED'""")

data = getData()

st.header("Trust Score Demo")
values = st.slider("Select a range of values", 0.0, 100.0, (0.0, 75.0))
st.write("Values:", values)

# Convert to numeric, coerce errors (non-numeric -> NaN), then fill NaN with 0
data['tag_value'] = pd.to_numeric(data['tag_value'], errors='coerce').fillna(0).astype(int)

# d = data[(data['tag_value'] >= values[0]) & (data['tag_value'] <= values[1])]
d = data[(data['tag_value'].astype(int) >= values[0]) & 
         (data['tag_value'].astype(int) <= values[1])]

col1, col2 = st.columns([3, 1])
with col1:
    st.scatter_chart(data=d, height=400, width=700, y="tag_value", x="table_name")
with col2:
    st.subheader("Filter Score")
    # fromdate = st.text_input("From (OrderDate)", value="2022-01-01")
    # todate = st.text_input("To (OrderDate)", value="2022-05-01")
    # d = data[(data['pickup_zip'] == int(pickup)) & (data['dropoff_zip'] == int(dropoff))]
    # st.write(f"# **${d['SalesAmount'].mean() if len(d) > 0 else 99:.2f}**")

st.dataframe(data=d, height=600, use_container_width=True)
