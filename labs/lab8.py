"""
Lab: Retrieval vs. Reranking in RAG
IST 488/688 - Building Human-Centered AI Applications
"""
 
docs = [
    "The midterm exam will be held on October 14 during class time.",
    "Homework 3 is due before the midterm review session.",
    "The final project rubric is posted on Blackboard.",
    "Office hours are Tuesdays from 3–5 PM.",
    "The midterm review session will cover Chapters 1 through 4.",
    "Quiz 2 covers retrieval, embeddings, and reranking."
]
 
query = "When is the midterm?"
 
 
# ── Part 1: Retrieval ──────────────────────────────────────────────────────────
 
def retrieval_score(query, doc):
    query_words = set(query.lower().split())
    doc_words = set(doc.lower().split())
    return len(query_words & doc_words)
 
scored_docs = [(doc, retrieval_score(query, doc)) for doc in docs]
scored_docs.sort(key=lambda x: x[1], reverse=True)
top_3 = scored_docs[:3]
 
print("=" * 60)
print("PART 1: Top 3 Retrieved Documents (by keyword overlap)")
print("=" * 60)
for i, (doc, score) in enumerate(top_3, 1):
    print(f"{i}. [Score: {score}] {doc}")
 
 
# ── Part 2: Reranking ──────────────────────────────────────────────────────────
 
def rerank_score(doc):
    score = 0
    doc_lower = doc.lower()
    if "midterm" in doc_lower:
        score += 2
    if "exam" in doc_lower:
        score += 2
    if any(char.isdigit() for char in doc):
        score += 3
    return score
 
reranked = [(doc, rerank_score(doc)) for doc, _ in top_3]
reranked.sort(key=lambda x: x[1], reverse=True)
 
print("\n" + "=" * 60)
print("PART 2: Reranked Top 3 Documents")
print("=" * 60)
for i, (doc, score) in enumerate(reranked, 1):
    print(f"{i}. [Rerank Score: {score}] {doc}")
 
 
# ── Part 3: Final Answer ───────────────────────────────────────────────────────
 
final_answer = reranked[0][0]
 
print("\n" + "=" * 60)
print("PART 3: Final Answer")
print("=" * 60)
print(f"→ {final_answer}")
 
 
