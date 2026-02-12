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
st.title("Lab 4: Chatbot using RAG")
st.markdown("---")

# ===== ChromaDB Setup ====
# Create ChromaDB client with a stable, writable path
db_path = Path.home() / ".cache" / "lab4_chroma"
db_path.mkdir(parents=True, exist_ok=True)
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

# Define the path to PDF files relative to this file
pdf_folder = Path(__file__).parent / "lab4_data"
pdf_files = list(pdf_folder.glob("*.pdf")) if pdf_folder.exists() else []

# Rebuild if the persisted DB is missing PDFs
if existing_count < len(pdf_files):
    try:
        chroma_client.delete_collection(name="Lab4Collection")
    except Exception:
        shutil.rmtree(db_path, ignore_errors=True)

    chroma_client = chromadb.PersistentClient(path=str(db_path))
    collection = chroma_client.get_or_create_collection(name="Lab4Collection")
    existing_count = 0

if existing_count == 0:
    if pdf_folder.exists() and pdf_folder.is_dir():
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


# After your existing code where you stored the collection...
st.session_state.vector_db = collection


# Display collection info
st.sidebar.write(f"📚 Documents in database: {st.session_state.vector_db.count()}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about the church documents"):
    
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # QUERY THE VECTOR DATABASE
    # Step 1: Create embedding for user's question
    query_embedding = st.session_state.openai_client.embeddings.create(
        input=prompt,
        model="text-embedding-3-small"
    ).data[0].embedding
    
    # Step 2: Search the vector database for relevant documents
    results = st.session_state.vector_db.query(
        query_embeddings=[query_embedding],
        n_results=3  # Get top 3 most relevant documents
    )
    
    # Step 3: Extract the relevant context
    relevant_docs = results['documents'][0]  # List of relevant document texts
    context = "\n\n".join(relevant_docs)
    
    # Step 4: Create enhanced prompt with context
    enhanced_prompt = f"""Use the following context from church documents to answer the question.
    
Context:
{context}

Question: {prompt}

Answer based on the context above. If the answer is not in the context, say so."""
    
    # Step 5: Get response from ChatGPT with context
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions about church documents. Use the provided context to answer accurately."},
                {"role": "user", "content": enhanced_prompt}
            ],
            stream=True
        )
        response = st.write_stream(stream)
    
    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})

# Optional: Show what documents were retrieved (for debugging)
def _quote_under_20_words(text: str) -> str:
    words = text.split()
    excerpt = " ".join(words[:20])
    if len(words) > 20:
        excerpt += " ..."
    return f'"{excerpt}"'


if st.sidebar.checkbox("Show retrieved documents"):
    if 'results' in locals():
        for doc in results['documents'][0]:
            st.sidebar.write(_quote_under_20_words(doc))



