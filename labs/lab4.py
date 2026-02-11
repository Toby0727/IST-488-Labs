import PyPDF2
import streamlit as st
from openai import OpenAI
import sys
import shutil
from pathlib import Path
from PyPDF2 import PdfReader

# Ensure ChromaDB uses a compatible SQLite
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules["pysqlite3"]

import chromadb


# Page config
st.set_page_config(page_title="lab 4", initial_sidebar_state="expanded")
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ===== BIG TITLE =====
st.title("CHURCH BOT 🤖⛪️")
st.markdown("---")

# ===== ChromaDB Setup ====
# Create ChromaDB client with a stable path relative to this file
db_path = Path(__file__).parent / "ChromaDB_for_lab"
chroma_client = chromadb.PersistentClient(path=str(db_path))
collection = chroma_client.get_or_create_collection(name="Lab4Collection")

# Create OpenAI client
if 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)

# A function that will add documents to collection
# Collection = collection, already established
# text = extraced text from PDF files
# Embeddings inserted into the collection from OpenAI

# Check if collection is already populated (avoid re-embedding)
try:
    existing_count = collection.count()
except Exception:
    st.sidebar.warning("ChromaDB failed to load existing data. Rebuilding index.")
    # Best-effort cleanup when the persisted DB is incompatible or corrupted
    try:
        chroma_client.delete_collection(name="Lab4Collection")
    except Exception:
        try:
            shutil.rmtree(db_path, ignore_errors=True)
        except Exception:
            pass

    chroma_client = chromadb.PersistentClient(path=str(db_path))
    collection = chroma_client.get_or_create_collection(name="Lab4Collection")
    existing_count = 0

    
#embed and store

if existing_count == 0:
    # Define the path to PDF files relative to this file
    pdf_folder = Path(__file__).parent / "lab4_data"
    
    if pdf_folder.exists() and pdf_folder.is_dir():
        pdf_files = list(pdf_folder.glob("*.pdf"))
        
        # Process each PDF file
        for pdf_file in pdf_files:
            try:
                # Read PDF and extract text
                print(f"Processing {pdf_file.name}...")
                pdf_reader = PyPDF2.PdfReader(str(pdf_file))
                text_content = ""
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                # Add to collection if there's content

                if text_content.strip():
                    # Create embedding using OpenAI "text-embedding-3-small"
                    embedding = st.session_state.openai_client.embeddings.create(
                        input=text_content,
                        model="text-embedding-3-small"  # OpenAI embeddings model
                    ).data[0].embedding
                    
            
                    # Add to ChromaDB collection
                    collection.add(
                        documents=[text_content],      # The text
                        embeddings=[embedding],         # The vector from OpenAI
                        ids=[pdf_file.name],           # Unique ID (filename)
                        metadatas=[{"filename": pdf_file.name}]  # Metadata
                    )
                    
            except Exception as e:
                st.sidebar.error(f"Error loading {pdf_file.name}: {str(e)}")

st.session_state.vector_db = collection

st.title("Lab 4: Chatbot using RAG")

# Page config
st.set_page_config(page_title="Lab 3: Streaming Chatbot", initial_sidebar_state="expanded")
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ===== BIG TITLE =====
st.title("CHURCH BOT 🤖⛪️")
st.markdown("---")

# ===== MODEL SELECTOR =====
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
    index=0
)

# ===== BUFFER TYPE SELECTOR =====
buffer_type = st.sidebar.radio(
    "Buffer Type:",
    options=["Message-based", "Token-based"],
    index=0
)

# ===== BUFFER CONTROLS =====
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

# ===== SYSTEM PROMPT =====
SYSTEM_PROMPT = {
    "role": "system",
    "content": """You are a helpful educational assistant that explains things in a way that 10-year-olds can understand.

After answering each question:
1. Give a clear, simple answer that a 10-year-old can understand
2. Then ask: "Do you want more info?"

Ways to offer more info (vary these, don't repeat the same phrase):
- "Want to know more about this?"
- "Should I explain that part in more detail?"
- "Curious about how that works?"
- "There's more cool stuff about this - interested?"
- "I can tell you more if you'd like!"
- Sometimes just end naturally without always asking

If the user wants more information:
- Provide additional details in a friendly, conversational way
- Keep it simple and fun for a 10-year-old
- You can ask if they want even more, but mix it up

If the user doesn't want more or changes topic:
- Be friendly and ready for their next question
- Don't force the "Do you want more info?" pattern
- Do more emojis in your responses to keep it fun and engaging!

Remember: Always use simple words and fun examples that kids can relate to!"""
}

# ===== HELPER FUNCTIONS =====
def count_tokens_approximate(messages):
    """Approximate token count: 1 token ≈ 4 characters"""
    total_chars = 0
    for message in messages:
        total_chars += len(message.get("role", ""))
        total_chars += len(message.get("content", ""))
        total_chars += 20
    return total_chars // 4

def get_buffered_messages(all_messages, buffer_size=2):
    """
    Keep system prompt + last N user/assistant message pairs
    System prompt is ALWAYS kept!
    """
    if len(all_messages) == 0:
        return []
    
    # Extract system prompt (should be first message)
    system_prompt = all_messages[0] if all_messages[0]["role"] == "system" else None
    
    # Get conversation messages (everything after system prompt)
    conversation = all_messages[1:] if system_prompt else all_messages
    
    # If conversation is short, return system + all conversation
    if len(conversation) <= buffer_size * 2:
        return [system_prompt] + conversation if system_prompt else conversation
    
    # Keep only last (buffer_size * 2) conversation messages
    buffered_conversation = conversation[-(buffer_size * 2):]
    
    # Return system prompt + buffered conversation
    return [system_prompt] + buffered_conversation if system_prompt else buffered_conversation

def get_token_buffered_messages(all_messages, max_tokens=1000):
    """
    Keep system prompt + messages that fit within token limit
    System prompt is ALWAYS kept!
    """
    if not all_messages:
        return []
    
    # Extract system prompt (should be first message)
    system_prompt = all_messages[0] if all_messages[0]["role"] == "system" else None
    
    # Get conversation messages
    conversation = all_messages[1:] if system_prompt else all_messages
    
    # Count system prompt tokens
    system_tokens = count_tokens_approximate([system_prompt]) if system_prompt else 0
    
    # Calculate remaining tokens for conversation
    remaining_tokens = max_tokens - system_tokens
    
    if remaining_tokens <= 0:
        return [system_prompt] if system_prompt else []
    
    # Build buffered conversation from most recent messages
    buffered = []
    current_tokens = 0
    
    for message in reversed(conversation):
        message_tokens = count_tokens_approximate([message])
        if current_tokens + message_tokens > remaining_tokens:
            break
        buffered.insert(0, message)
        current_tokens += message_tokens
    
    # Return system prompt + buffered conversation
    return [system_prompt] + buffered if system_prompt else buffered

# Initialize session state WITH system prompt
if "messages" not in st.session_state:
    st.session_state.messages = [SYSTEM_PROMPT]

# Display all previous messages (skip system prompt)
for message in st.session_state.messages:
    if message["role"] != "system":  # Don't show system prompt to user
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Get user input
if prompt := st.chat_input("Feel free to open up to me"):
    
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Create buffered messages (ALWAYS includes system prompt)
    if buffer_type == "Message-based":
        buffered_messages = get_buffered_messages(st.session_state.messages, buffer_size)
    else:
        buffered_messages = get_token_buffered_messages(st.session_state.messages, max_tokens)
    
    # Display statistics
    tokens_in_buffer = count_tokens_approximate(buffered_messages)
    total_tokens = count_tokens_approximate(st.session_state.messages)
    
    st.sidebar.divider()
    st.sidebar.write("**Buffer Statistics:**")
    st.sidebar.write(f"Messages in buffer: {len(buffered_messages)}")
    st.sidebar.write(f"Total messages: {len(st.session_state.messages)}")
    st.sidebar.write(f"Approx tokens in buffer: ~{tokens_in_buffer}")
    st.sidebar.write(f"Approx total tokens: ~{total_tokens}")
    st.sidebar.write(f"System prompt included: ✅")
    
    # Get and display assistant response
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model_option,
            messages=buffered_messages,  # Includes system prompt!
            stream=True
        )
        response = st.write_stream(stream)
    
    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})