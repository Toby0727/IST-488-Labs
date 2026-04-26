"""
humanize.py — LLM-powered text humanizer for philosophy/academic writing
Requires: pip install anthropic
Set ANTHROPIC_API_KEY environment variable before running.

Usage:
    python humanize.py
    (paste your text when prompted, press Enter twice when done)
"""

import anthropic
import tomllib

with open(".streamlit/secrets.toml", "rb") as f:
    secrets = tomllib.load(f)

SYSTEM_PROMPT = """
You are an expert editor who rewrites AI-generated academic and philosophy text to sound like it was written by a thoughtful human writer.

Apply these rules:

1. VARY SENTENCE LENGTH — mix short punchy sentences with longer ones. Occasionally use a one or two-word sentence for emphasis.

2. USE CONTRACTIONS NATURALLY — "it's", "don't", "they're" etc. But don't overdo it — keep some academic register where appropriate.

3. KILL FILLER PHRASES — replace or delete:
   - "it is important to note that" → just say it
   - "it is worth mentioning" → just say it
   - "furthermore / moreover / in addition" → "also", "and", or nothing
   - "in conclusion" → "so" or "ultimately"
   - "utilize" → "use"
   - "facilitate" → "help" or "enable"
   - "endeavor" → "try"
   - "demonstrate" → "show"
   - "in order to" → "to"
   - "due to the fact that" → "because"
   - "a wide range of" → "many"
   - "it could be argued that" → "arguably"

4. BE DIRECT — cut hedging, use concrete language, let the writing have a mild point of view.

5. BREAK SYMMETRY — vary paragraph and list structure. Not everything needs a topic sentence and a conclusion.

6. PRESERVE all facts, citations, arguments, and meaning exactly. Do not add new claims.

7. KEEP the academic register — this is a philosophy paper, not a blog post. Just make it sound like a real person wrote it.

Return ONLY the rewritten text. No commentary, no preamble, no explanation.
""".strip()


def humanize_text(text: str) -> str:
    client = anthropic.Anthropic(api_key=secrets["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Rewrite the following philosophy paper text:\n\n{text}"
            }
        ]
    )
    return message.content[0].text


if __name__ == "__main__":
    print("Paste your text below. Press Enter twice when done.\n")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    text = "\n".join(lines).strip()
    if not text:
        print("No input provided.")
    else:
        print("\n--- HUMANIZED OUTPUT ---\n")
        print(humanize_text(text))