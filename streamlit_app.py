import streamlit as st
import openai as openai


st.set_page_config(page_title='IST 488 Lab', initial_sidebar_state='expanded')

lab1 = st.Page('labs/lab1.py', title='lab 1')
lab2 = st.Page('labs/lab2.py', title='lab 2')
lab3 = st.Page('labs/lab3(Toby).py', title='lab 3')
lab4 = st.Page('labs/lab4.py', title='lab 4')
lab5 = st.Page('labs/lab5.py', title='lab 5', default=True)
lab6 = st.Page('labs/lab6.py', title='lab 6')
lab9 = st.Page('labs/lab9.py', title='lab 9')
humanize = st.Page('labs/humanize.py', title='humanize')
pg = st.navigation([lab1, lab2, lab3, lab4, lab5, lab6, lab9])
pg.run()

