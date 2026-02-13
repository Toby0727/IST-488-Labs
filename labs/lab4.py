import PyPDF2
import streamlit as st
from openai import OpenAI
import sys
import shutil
from pathlib import Path

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

# ===== CHUNKING FUNCTION =====
def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Split text into overlapping chunks
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < text_length:
            last_period = max(chunk.rfind('.'), chunk.rfind('?'), chunk.rfind('!'))
            if last_period != -1 and last_period > chunk_size * 0.5:
                end = start + last_period + 1
                chunk = text[start:end]
        
        chunks.append(chunk.strip())
        start = end - overlap if end < text_length else text_length
    
    return chunks


# ===== ChromaDB Setup ====
# Create ChromaDB client with a stable, writable path
db_path = Path.home() / ".cache" / "lab4_chroma"
db_path.mkdir(parents=True, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=str(db_path))
collection = chroma_client.get_or_create_collection(name="Lab4Collection")

# Create OpenAI client
if 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)

# Check if collection is already populated (avoid re-embedding)
try:
    existing_count = collection.count()
except Exception:
    st.sidebar.warning("ChromaDB failed to load existing data. Rebuilding index.")
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
        st.sidebar.info("Processing PDFs with chunking...")
        
        # Process each PDF file WITH CHUNKING
        for pdf_file in pdf_files:
            try:
                # Read PDF and extract text
                st.sidebar.info(f"Processing {pdf_file.name}...")
                pdf_reader = PyPDF2.PdfReader(str(pdf_file))
                text_content = ""
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                # CHUNK THE TEXT
                if text_content.strip():
                    chunks = chunk_text(text_content, chunk_size=1000, overlap=200)
                    st.sidebar.info(f"  → Split into {len(chunks)} chunks")
                    
                    # Add each chunk to the collection
                    for i, chunk in enumerate(chunks):
                        # Create embedding for this chunk
                        embedding = st.session_state.openai_client.embeddings.create(
                            input=chunk,
                            model="text-embedding-3-small"
                        ).data[0].embedding
                        
                        # Add to ChromaDB collection with unique ID per chunk
                        collection.add(
                            documents=[chunk],
                            embeddings=[embedding],
                            ids=[f"{pdf_file.name}_chunk_{i}"],
                            metadatas=[{
                                "filename": pdf_file.name,
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            }]
                        )
                    
                    st.sidebar.success(f"✅ Loaded: {pdf_file.name} ({len(chunks)} chunks)")
                    
            except Exception as e:
                st.sidebar.error(f"Error loading {pdf_file.name}: {str(e)}")


# Store collection in session state
st.session_state.Lab4_VectorDB = collection

st.sidebar.write(
    f"📚 Chunks in database: {st.session_state.Lab4_VectorDB.count()}"
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about IST courses"):
    
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # ALWAYS QUERY THE VECTOR DATABASE FIRST
    # Step 1: Create embedding for user's question
    query_embedding = st.session_state.openai_client.embeddings.create(
        input=prompt,
        model="text-embedding-3-small"
    ).data[0].embedding
    
    # Step 2: Search the vector database for relevant chunks
    results = st.session_state.Lab4_VectorDB.query(
        query_embeddings=[query_embedding],
        n_results=5  # Get top 5 most relevant chunks
    )
    
    # Step 3: Extract the relevant context
    relevant_docs = results.get("documents", [[]])[0]
    context = "\n\n---\n\n".join(relevant_docs) if relevant_docs else ""
    
    # Get unique filenames from chunks
    filenames = set()
    for metadata in results.get("metadatas", [[]])[0]:
        filenames.add(metadata.get("filename", "Unknown"))
    files_used = ", ".join(sorted(filenames))
    
    # Step 4: Create system prompt that handles BOTH cases
    system_prompt = """You are an IST course information assistant with access to course syllabus documents.

CRITICAL INSTRUCTIONS:
1. You will be provided with context from IST course documents
2. FIRST, check if the answer is in the provided context
3. If the answer IS in the context:
   - Start with: "Based on [filename]..." or "According to [filename]..."
   - Cite which specific file(s) you're using
   - Answer using ONLY the information from the context
   
4. If the answer is NOT in the context:
   - Start with: "I didn't find this in the course documents, but..."
   - Then provide an answer using your general knowledge
   - Be helpful and informative
   
5. Be clear about which case you're in (found in docs vs. using general knowledge)

Examples:
- Found in docs: "Based on IST140_syllabus.pdf, the course prerequisites are..."
- Not found: "I didn't find this in the course documents, but I can help explain. Python is a programming language..."
"""

    enhanced_prompt = f"""Context from IST course documents: {files_used}

{context}

User Question: {prompt}

Instructions: 
- If the answer is in the context above, cite your sources and answer based on the documents
- If the answer is NOT in the context, say "I didn't find this in the course documents, but..." and provide a helpful answer using general knowledge"""
    
    # Step 5: Get response from ChatGPT
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_prompt}
            ],
            stream=True
        )
        response = st.write_stream(stream)
    
    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Store results for sidebar display
    st.session_state.last_results = results

# Sidebar to show retrieved chunks
if st.sidebar.checkbox("Show retrieved chunks"):
    if hasattr(st.session_state, 'last_results') and st.session_state.last_results:
        results = st.session_state.last_results
        st.sidebar.write("### Retrieved Chunks:")
        
        for i, metadata in enumerate(results["metadatas"][0], 1):
            filename = metadata.get("filename", "Unknown")
            chunk_idx = metadata.get("chunk_index", 0)
            total = metadata.get("total_chunks", 1)
            st.sidebar.write(f"{i}. **{filename}** (chunk {chunk_idx + 1}/{total})")
        
    else:
        st.sidebar.write("No retrieval performed yet.")

# Clear chat button
if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()
