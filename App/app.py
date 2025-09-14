import streamlit as st

pages = {
    "Your views": [
        st.Page("use_case_view.py", title="Use Case View"),
    ],
}

pg = st.navigation(pages)
pg.run()