import streamlit as st
from openai import OpenAI

# --- Config ---
st.set_page_config(page_title="Lab 3: Streaming Chatbot", initial_sidebar_state="expanded")
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# --- Parameters ---
MAX_TOKENS = st.sidebar.number_input("Max tokens in buffer", min_value=256, max_value=4096, value=1024, step=64)

# --- Tokenizer (using OpenAI's token counting) ---
def count_tokens(messages):
    # Approximate token count: ~4 chars per token on average
    total_chars = 0
    for msg in messages:
        total_chars += len(msg.get("content", "")) + 4  # metadata overhead
    return max(1, total_chars // 4)

# --- Conversation Buffer ---
def get_buffered_messages(messages, max_tokens):
    # Always keep the system prompt
    system_prompt = messages[0]
    rest = messages[1:]
    # Only keep last two user/assistant pairs
    pairs = []
    i = len(rest) - 1
    while i >= 0:
        if rest[i]["role"] == "user":
            if i + 1 < len(rest) and rest[i + 1]["role"] == "assistant":
                pairs.insert(0, [rest[i], rest[i + 1]])
            else:
                pairs.insert(0, [rest[i]])
        i -= 1
    # Flatten and keep only last two pairs
    flat = [msg for pair in pairs[-2:] for msg in pair]
    buffer = [system_prompt] + flat
    # Token-based buffer
    while count_tokens(buffer) > max_tokens and len(flat) > 2:
        flat = flat[2:]  # remove oldest pair
        buffer = [system_prompt] + flat
    return buffer

# --- System Prompt ---
SYSTEM_PROMPT = (
    "You are a helpful assistant for kids. "
    "Always answer so a 10-year-old can understand. "
    "After each answer, ask: 'Do you want more info?' "
    "If user says 'yes', give more info and ask again. "
    "If user says 'no', ask what else you can help with."
)

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

st.title("Lab 3: Streaming Chatbot")

# --- Chat UI ---
for msg in st.session_state.messages[1:]:
    st.chat_message(msg["role"]).write(msg["content"])

user_input = st.chat_input("Ask me anything!")

def stream_chat(messages):
    response = ""
    with client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        stream=True,
        max_tokens=256,
        temperature=0.7,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                response += delta.content
                yield delta.content
    return response

if user_input:
    # Handle "Do you want more info?" logic
    last_bot = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
    if last_bot and last_bot["content"].strip().endswith("Do you want more info?"):
        if user_input.lower() in ["yes", "y"]:
            st.session_state.messages.append({"role": "user", "content": user_input})
            buffered = get_buffered_messages(st.session_state.messages, MAX_TOKENS)
            with st.chat_message("assistant"):
                placeholder = st.empty()
                response = ""
                for chunk in stream_chat(buffered):
                    response += chunk
                    placeholder.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        elif user_input.lower() in ["no", "n"]:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("assistant"):
                response = "Okay! What else can I help you with?"
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("assistant"):
                response = "Please answer 'yes' or 'no'. Do you want more info?"
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        buffered = get_buffered_messages(st.session_state.messages, MAX_TOKENS)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            response = ""
            for chunk in stream_chat(buffered):
                response += chunk
                placeholder.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# --- Token Count Display ---
buffered = get_buffered_messages(st.session_state.messages, MAX_TOKENS)
st.sidebar.info(f"Tokens sent to LLM: {count_tokens(buffered)}")