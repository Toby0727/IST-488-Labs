import streamlit as st
import openai as openai
lab1 = st.Page('labs/lab1.py' , title = 'lab 1')
lab2 = st.Page('labs/lab2.py' , title = 'lab 2')
lab3 = st.Page('labs/lab3(Toby).py' , title = 'lab 3', default=True)
pg = st.navigation([lab1, lab2, lab3])
st.set_page_config(page_title= 'IST 488 Lab', initial_sidebar_state='expanded')
pg.run()

