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
st.session_state.Lab4_VectorDB = collection


st.sidebar.write(
    f"📚 Documents in database: {st.session_state.Lab4_VectorDB.count()}"
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about ist courses"):
    
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
    results = st.session_state.Lab4_VectorDB.count(
        query_embeddings=[query_embedding],
        n_results=3  # Get top 3 most relevant documents
    )
    
    # Step 3: Extract the relevant context
    relevant_docs = results['documents'][0]  # List of relevant document texts
    context = "\n\n".join(relevant_docs)
    
    # Step 4: Create enhanced prompt with context
    system_prompt = """You are an information assistant with access to specific ist course syllabus documents. Use the provided context to answer the user's question. Always cite your sources from the context when answering. If the information is not in the context, say so.

CRITICAL REQUIREMENTS:
1. You MUST declare which specific file(s) you are using to answer each question
2. Format your responses like this:
   - "Based on [filename], [answer]..."
   - "According to [filename], [answer]..."
   - "Using information from [filename], [answer]..."

3. ALWAYS mention the filename at the START of your response

4. When using multiple files, list them: "Based on file1.pdf and file2.pdf..."

5. When information is NOT in the documents:
   - State: "I cannot find this information in the provided ist course syllabus documents."

6. Be specific - always declare your source file!

Example good responses:
- "Based on mission_statement.pdf, the church's mission is..."
- "According to bylaws.pdf and history.pdf, the church was founded..."
- "I cannot find this information in the provided ist course syllabus documents (searched: bylaws.pdf, history.pdf, events.pdf)."

Remember: ALWAYS declare which file you're using!"""

    enhanced_prompt = f"""Use the following context from ist courses to answer the question.

Context:
{context}

Question: {prompt}

Answer based on the context above. If the answer is not in the context, say so."""
    
    # Step 5: Get response from ChatGPT with context
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

# Sidebar to show retrieved documents
if st.sidebar.checkbox("Show retrieved documents"):
    if "results" in locals() and results:
        st.sidebar.write("### Retrieved Files:")
        # results["metadatas"][0] contains metadata for top matches
        for metadata in results["metadatas"][0]:
            st.sidebar.write(f"- {metadata['filename']}")
    else:
        st.sidebar.write("No retrieval performed yet.")