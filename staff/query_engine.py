from .vector_store import embed_texts

def answer_query(index, query, chunks, threshold=1.2):
    if not chunks:
        return "⚠️ Handbook content not available. Please upload a valid policy document."

    try:
        q_vector = embed_texts([query]).astype("float32")
        D, I = index.search(q_vector, k=1)

        if len(D[0]) == 0 or len(I[0]) == 0:
            return "⚠️ No content available in the index. Please check handbook upload."

        if D[0][0] < threshold:
            return chunks[I[0][0]]  # Closest matching answer

        return "Sorry, no matching policy found."

    except Exception as e:
        print("[Answer Engine ERROR]", e)
        return "❌ Failed to search policy database."
