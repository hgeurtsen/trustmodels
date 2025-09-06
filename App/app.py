import streamlit as st

pages = {
    "Your views": [
        st.Page("trust_score_view.py", title="Trust Score View"),
        st.Page("table_view.py", title="Table View"),
    ],
}

pg = st.navigation(pages)
pg.run()