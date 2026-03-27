import streamlit as st
from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🎬 Movie Recommender",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Movie Recommendation Chatbot")
st.caption("Powered by LangChain · Anthropic Claude")

# ── Part D: Model initialization ──────────────────────────────────────────────
# Anthropic (default)
llm = init_chat_model(
    "claude-haiku-4-5-20251001",
    model_provider="anthropic",
    api_key=st.secrets["ANTHROPIC_API_KEY"],
)

# OpenAI (Part D — swap by commenting the block above and uncommenting below)
# llm = init_chat_model(
#     "gpt-4o-mini",
#     model_provider="openai",
#     api_key=st.secrets["OPENAI_API_KEY"],
# )

# ── Part A: Sidebar controls ──────────────────────────────────────────────────
st.sidebar.header("🎛️ Your Preferences")

genre = st.sidebar.selectbox(
    "Genre",
    ["Action", "Comedy", "Horror", "Drama", "Sci-Fi", "Thriller", "Romance"],
)

mood = st.sidebar.selectbox(
    "Your Mood",
    ["Excited", "Happy", "Sad", "Bored", "Scared", "Romantic", "Curious", "Tense", "Melancholy"],
)

persona = st.sidebar.selectbox(
    "Recommender Persona",
    ["Film Critic", "Casual Friend", "Movie Journalist"],
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Tip:** Try different persona + mood combos — the tone of the recommendations changes!"
)

# ── Part B: Recommendation Chain ─────────────────────────────────────────────

recommendation_template = PromptTemplate(
    input_variables=["genre", "mood", "persona"],
    template="""You are a {persona}. A user is feeling {mood} and wants to watch a {genre} movie.

Recommend exactly 3 movies that fit their mood and genre. For each movie, provide:
- The movie title and release year
- A 2–3 sentence description
- Why it matches their current mood

Write in the natural voice and tone of a {persona}. Be specific, opinionated, and genuine.
""",
)

recommendation_chain = recommendation_template | llm | StrOutputParser()

# Session state
if "last_recommendation" not in st.session_state:
    st.session_state.last_recommendation = ""

# Recommendation button
if st.button("🎥 Get Recommendations", type="primary"):
    with st.spinner("Finding the perfect movies for you..."):
        response = recommendation_chain.invoke({
            "genre": genre,
            "mood": mood,
            "persona": persona,
        })
        st.session_state.last_recommendation = response

# Display recommendation
if st.session_state.last_recommendation:
    st.subheader(f"🍿 Recommendations · {genre} · {mood} · via {persona}")
    st.markdown(st.session_state.last_recommendation)

# ── Part C: Follow-Up Chain ───────────────────────────────────────────────────
st.divider()
follow_up = st.text_input("💬 Ask a follow-up question about these movies:")

followup_template = PromptTemplate(
    input_variables=["recommendations", "question"],
    template="""Here are some movie recommendations that were given to a user:

{recommendations}

The user now has a follow-up question: {question}

Answer the question helpfully and specifically, referencing the movies above where relevant.
""",
)

followup_chain = followup_template | llm | StrOutputParser()

if follow_up:
    if not st.session_state.last_recommendation:
        st.warning("Get recommendations first, then ask a follow-up question!")
    else:
        with st.spinner("Looking that up..."):
            followup_response = followup_chain.invoke({
                "recommendations": st.session_state.last_recommendation,
                "question": follow_up,
            })
        st.subheader("🔍 Follow-Up Answer")
        st.markdown(followup_response)