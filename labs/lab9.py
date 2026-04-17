import streamlit as st
import json
import os
from anthropic import Anthropic

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Long-Term Memory Chatbot", page_icon="🧠")

# ── API client ───────────────────────────────────────────────────────────────
client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

MEMORIES_FILE = "memories.json"
MAIN_MODEL    = "claude-sonnet-4-20250514"
EXTRACT_MODEL = "claude-haiku-4-5-20251001"   # cheap model for extraction

# ── Memory helpers ────────────────────────────────────────────────────────────
def load_memories() -> list[str]:
    if os.path.exists(MEMORIES_FILE):
        with open(MEMORIES_FILE, "r") as f:
            return json.load(f)
    return []

def save_memories(memories: list[str]) -> None:
    with open(MEMORIES_FILE, "w") as f:
        json.dump(memories, f, indent=2)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🧠 Long-Term Memory")
memories = load_memories()
if memories:
    for i, mem in enumerate(memories, 1):
        st.sidebar.markdown(f"**{i}.** {mem}")
else:
    st.sidebar.info("No memories yet. Start chatting!")

if st.sidebar.button("🗑️ Clear All Memories"):
    save_memories([])
    st.rerun()

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("🧠 Chatbot with Long-Term Memory")
st.caption("I remember facts about you across conversations — even after you refresh!")

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Say something…"):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build system prompt, injecting long-term memories
    memories = load_memories()
    system_prompt = (
        "You are a helpful, friendly assistant with long-term memory. "
        "You remember facts about the user from previous conversations."
    )
    if memories:
        memory_block = "\n".join(f"- {m}" for m in memories)
        system_prompt += (
            f"\n\nHere are things you remember about this user from past conversations:\n"
            f"{memory_block}\n\n"
            "Use this context naturally when it's relevant — don't recite it robotically."
        )

    # ── Main LLM call ─────────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            response = client.messages.create(
                model=MAIN_MODEL,
                max_tokens=1024,
                system=system_prompt,
                messages=st.session_state.messages,
            )
        reply = response.content[0].text
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # ── Memory extraction (second LLM call) ───────────────────────────────────
    existing = "\n".join(f"- {m}" for m in memories) if memories else "None yet."
    extract_prompt = f"""You are a memory extraction assistant.

Analyze the user message and assistant response below and identify any NEW facts
worth remembering about the user — such as their name, location, occupation,
hobbies, preferences, or personal details.

Do NOT repeat facts already in the existing memories.
Return ONLY a JSON array of short strings (one fact per string).
If there is nothing new to remember, return an empty array: []

Existing memories:
{existing}

User message: {prompt}
Assistant response: {reply}

Return ONLY valid JSON. No explanation, no markdown fences."""

    try:
        extract_resp = client.messages.create(
            model=EXTRACT_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": extract_prompt}],
        )
        raw = extract_resp.content[0].text.strip()
        # Strip markdown fences if present
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        new_facts: list[str] = json.loads(raw)
        if new_facts:
            updated = memories + new_facts
            save_memories(updated)
            st.rerun()   # refresh sidebar
    except (json.JSONDecodeError, Exception):
        pass  # silently ignore extraction failures
