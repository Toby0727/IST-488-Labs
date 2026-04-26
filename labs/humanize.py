import streamlit as st
import anthropic

st.set_page_config(page_title="Humanizer", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:ital,wght@0,400;0,500;1,400&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0f0f0f;
    color: #e8e8e8;
}

h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #555 !important;
    border-bottom: 1px solid #222;
    padding-bottom: 12px;
    margin-bottom: 24px !important;
}

.stTextArea textarea {
    background-color: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 4px !important;
    color: #e8e8e8 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
}

.stTextArea textarea:focus {
    border-color: #444 !important;
    box-shadow: none !important;
}

.stButton > button {
    background-color: #e8e8e8 !important;
    color: #0f0f0f !important;
    border: none !important;
    border-radius: 3px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    padding: 8px 24px !important;
    transition: background 0.15s !important;
}

.stButton > button:hover {
    background-color: #ffffff !important;
}

.output-box {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 16px;
    font-size: 13px;
    line-height: 1.7;
    color: #c8ffc8;
    white-space: pre-wrap;
    margin-top: 8px;
}

label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: #555 !important;
}

.stMarkdown p { color: #999; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

st.title("// humanize_text — philosophy paper rewriter")

SYSTEM_PROMPT = """You are an expert editor who rewrites AI-generated academic and philosophy text to sound like it was written by a thoughtful human writer.

Apply these rules:
1. VARY SENTENCE LENGTH — mix short punchy sentences with longer ones.
2. USE CONTRACTIONS NATURALLY — "it's", "don't", "they're" etc. Keep some academic register.
3. KILL FILLER PHRASES — replace or delete: "it is important to note that", "furthermore", "moreover", "utilize", "facilitate", "endeavor", "in order to", "due to the fact that", "a wide range of", "it could be argued that".
4. BE DIRECT — cut hedging, use concrete language.
5. BREAK SYMMETRY — vary paragraph and list structure.
6. PRESERVE all facts, citations, arguments, and meaning exactly.
7. KEEP the academic register — this is a philosophy paper, not a blog post.

Return ONLY the rewritten text. No commentary, no preamble."""

input_text = st.text_area("Input — paste your text", height=280, placeholder="Paste your AI-generated philosophy text here...")

if st.button("Humanize →"):
    if not input_text.strip():
        st.warning("Paste some text first.")
    else:
        with st.spinner("Rewriting..."):
            try:
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                message = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": f"Rewrite the following philosophy paper text:\n\n{input_text}"}]
                )
                result = message.content[0].text
                st.markdown("**Output — humanized**")
                st.markdown(f'<div class="output-box">{result}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")