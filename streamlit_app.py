import streamlit as st
import openai as openai
lab1 = st.Page('labs/lab1.py' , title = 'lab 1')
lab2 = st.Page('labs/lab2.py' , title = 'lab 2', default=True)
lab3 = st.Page('labs/lab3.py' , title = 'lab 3')
lab3_toby = st.Page('labs/lab3.py' , title = 'lab 3 toby')
pg = st.navigation([lab1, lab2, lab3, lab3_toby])
st.set_page_config(page_title= 'IST 488 Lab', initial_sidebar_state='expanded')
pg.run()

