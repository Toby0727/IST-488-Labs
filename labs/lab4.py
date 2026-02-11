import PyPDF2
import streamlit as st
from openai import OpenAI
import sys
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
#create ChromaDB client
chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_lab')
collection = chroma_client.get_or_create_collection(name="Lab4Collection")

# Create OpenAI client
if 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)

# A function that will add documents to collection
# Collection = collection, already established
# text = extraced text from PDF files
# Embeddings inserted into the collection from OpenAI

# Check if collection is already populated (avoid re-embedding)
existing_count = collection.count()

    
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

##### QUERYING A COLLECTION -- ONLY USED FOR TESTING ####

topic = st.sidebar.text_input(
    "Topic",
    placeholder="Type your topic (e.g., GenAI)..."
)

if topic:
    client = st.session_state.openai_client

    # Create embedding for the query
    response = client.embeddings.create(
        input=topic,
        model="text-embedding-3-small"
    )

    query_embedding = response.data[0].embedding

    # Query Chroma collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    # Display results
    st.subheader(f"Results for: {topic}")

    for i in range(len(results["documents"][0])):
        doc = results["documents"][0][i]
        doc_id = results["ids"][0][i]

        st.write(f"**{i+1}. {doc_id}**")
        st.write(doc[:500])  # Show first 500 chars
        st.divider()

else:
    st.info("Enter a topic in the sidebar to search the collection.")

