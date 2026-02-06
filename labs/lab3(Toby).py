import streamlit as st
from openai import OpenAI


# prompt and user
st.set_page_config(page_title="Lab 3: Streaming Chatbot", initial_sidebar_state="expanded")
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ===== BIG TITLE =====
st.title("🇹🇷 ASLINUR KNOWS IT ALL 🇹🇷")
st.markdown("---")

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

# ===== ADD THIS: BUFFER TYPE SELECTOR =====
buffer_type = st.sidebar.radio(
    "Buffer Type:",
    options=["Message-based", "Token-based"],
    index=0
)

# ===== ADD THIS: BUFFER CONTROLS =====
if buffer_type == "Message-based":
    buffer_size = st.sidebar.slider(
        "Number of exchanges to remember:",
        min_value=1,
        max_value=10,
        value=2,
        step=1
    )
    st.sidebar.write(f"**Keeping last {buffer_size} exchanges**")
else:
    max_tokens = st.sidebar.slider(
        "Max tokens for context:",
        min_value=100,
        max_value=20000,
        value=1000,
        step=100
    )
    st.sidebar.write(f"**Max tokens: {max_tokens}**")

# ===== ADD THESE HELPER FUNCTIONS =====
# TOKEN COUNTS

def count_tokens_approximate(messages):
    """
    Approximate token count without tiktoken
    Rule: 1 token ≈ 4 characters
    """
    total_chars = 0
    for message in messages:
        total_chars += len(message.get("role", ""))
        total_chars += len(message.get("content", ""))
        total_chars += 20  # Formatting overhead
    return total_chars // 4

def get_buffered_messages(all_messages, buffer_size=2):
    """Keep only the last N user/assistant message pairs"""
    if len(all_messages) <= buffer_size * 2:
        return all_messages
    return all_messages[-(buffer_size * 2):]

def get_token_buffered_messages(all_messages, max_tokens=1000):
    """Keep messages that fit within token limit"""
    if not all_messages:
        return []
    
    buffered = []
    current_tokens = 0
    
    for message in reversed(all_messages):
        message_tokens = count_tokens_approximate([message])
        if current_tokens + message_tokens > max_tokens:
            break
        buffered.insert(0, message)
        current_tokens += message_tokens
    
    return buffered

# Initialize session state FIRST (you already have this)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize session state FIRST
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display all previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input
if prompt := st.chat_input("Feel free to open up to me"):
    
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # ===== CREATE BUFFERED MESSAGES =====
    if buffer_type == "Message-based":
        buffered_messages = get_buffered_messages(st.session_state.messages, buffer_size)
    else:  # Token-based
        buffered_messages = get_token_buffered_messages(st.session_state.messages, max_tokens)
    
    # ===== DISPLAY BUFFER STATISTICS =====
    tokens_in_buffer = count_tokens_approximate(buffered_messages)
    total_tokens = count_tokens_approximate(st.session_state.messages)
    
    st.sidebar.divider()
    st.sidebar.write("**Buffer Statistics:**")
    st.sidebar.write(f"Messages in buffer: {len(buffered_messages)}")
    st.sidebar.write(f"Total messages: {len(st.session_state.messages)}")
    st.sidebar.write(f"Approx tokens in buffer: ~{tokens_in_buffer}")
    st.sidebar.write(f"Approx total tokens: ~{total_tokens}")
    
    # Get and display assistant response (streaming)
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model_option,
            messages=buffered_messages,  # ← FIX: Use buffered_messages!
            stream=True
        )
        response = st.write_stream(stream)
    
    # Save assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Save assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response})