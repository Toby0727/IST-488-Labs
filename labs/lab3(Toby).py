import streamlit as st
from openai import OpenAI


# prompt and user
st.set_page_config(page_title="Lab 3: Streaming Chatbot", initial_sidebar_state="expanded")
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# start chat
with st.chat_message("user"):
    st.write("hello dear, what is on your mind?")

prompt = st.text_input("Feel Free to Open up to me")
if prompt:
    with st.chat_message("user"):
        st.write(prompt)

# Initialize session state
# This stores the conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

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

# Display all previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):  # user or assistant
        st.markdown(message["content"])

# Get and display assistant response (streaming)
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model_option,
            messages=st.session_state.messages,
            stream=True  # Enable streaming for typing effect
        )
        response = st.write_stream(stream)
    
    # Save assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response})
