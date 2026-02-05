import streamlit as st
from openai import OpenAI


# prompt and user
st.set_page_config(page_title="Lab 3: Streaming Chatbot", initial_sidebar_state="expanded")
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ===== MODEL SELECTOR (DROPDOWN) =====
st.sidebar.title("Settings")
model_option = st.sidebar.selectbox(
    "Select Model:",
    options=[
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini"
    ],
    index=0  # Default to first option (gpt-3.5-turbo)
)

# Initialize session state FIRST
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display all previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input - CHANGE THIS PART
if prompt := st.chat_input("Feel free to open up to me"):  # ← Use st.chat_input instead
    
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get and display assistant response (streaming)
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model_option,
            messages=st.session_state.messages,
            stream=True
        )
        response = st.write_stream(stream)
    
    # Save assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response})