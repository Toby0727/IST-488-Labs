import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
st.set_page_config(page_title="Lab App", layout="wide")

# Create pages
pages = {
    "Lab 1": st.Page("Lab1.py", title="Lab 1"),
    "Lab 2": st.Page("Lab2.py", title="Lab 2"),
}

# Default page = Lab2
pg = st.navigation(pages, position="sidebar", default="Lab 2")

pg.run()