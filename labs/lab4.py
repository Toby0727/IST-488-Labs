import streamlit as st
from openai import OpenAI
import sys
import chromadb
from pathlib import Path
from PyPDF2 import PdfReader

# fixing
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules['pysqlite3']

#create ChromaDB client
chroma_client = chromadb.PresidentClient(path='./ChromaDB_for_lab')
collection = chroma_client.get_or_create_collection(name="Lab4Collection")

# Create OpenAI client
if 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)

# A function that will add documents to collection
# Collection = collection, already established
# text = extraced text from PDF files
# Embeddings inserted into the collection from OpenAI
def add_to_collection (collection, text, file_name):
    # Create embedding for the text
    embedding = st.session_state.openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    ).data[0].embedding

    # Add the text and its embedding to the collection
    collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[file_name]
    )

