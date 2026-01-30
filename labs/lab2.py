import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader

secret_key = st.secrets.OPENAI_API_KEY

def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

st.title("📄 Lab 2")

openai_api_key = secret_key
client = OpenAI(api_key=openai_api_key)

uploaded_file = st.file_uploader(
    "Upload a document (.txt or .pdf)", type=("txt", "pdf")
)

# Sidebar controls for summary type and model selection
st.sidebar.header("Summary Options")
summary_type = st.sidebar.selectbox(
    "Type of summary",
    [
        "Summarize in 100 words",
        "Summarize in 2 connecting paragraphs",
        "Summarize in 5 bullet points",
    ],
)

use_advanced = st.sidebar.checkbox("Use advanced model")

generate = st.sidebar.button("Generate Summary")

# When a file is uploaded and the user clicks Generate, produce a summary
if uploaded_file and generate:

    file_extension = uploaded_file.name.split(".")[-1]

    if file_extension == "txt":
        document = uploaded_file.read().decode("utf-8")

    elif file_extension == "pdf":
        document = read_pdf(uploaded_file)

    else:
        st.error("Unsupported file type.")
        st.stop()

    # Choose model based on user selection
    if use_advanced:
        model = "gpt-4o"
    else:
        model = 'gpt-3.5-turbo'

    # Include the summary type explicitly in the LLM instructions
    instruction = (
        f"{summary_type}. Provide the summary only and do not include the original document text."
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes documents."},
        {"role": "user", "content": f"{instruction}\n\nDocument:\n\n{document}"},
    ]

    with st.spinner("Generating summary..."):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

    summary = response.choices[0].message.content

    st.subheader("Summary")
    st.write(summary)


