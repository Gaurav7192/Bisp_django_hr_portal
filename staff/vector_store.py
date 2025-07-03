import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

VECTOR_STORE_PATH = "faiss.index"
model = SentenceTransformer("all-MiniLM-L6-v2")
vector_dim = 384

def load_or_create_index():
    if os.path.exists(VECTOR_STORE_PATH):
        return faiss.read_index(VECTOR_STORE_PATH)
    else:
        index = faiss.IndexFlatL2(vector_dim)
        faiss.write_index(index, VECTOR_STORE_PATH)
        return index

def save_index(index):
    faiss.write_index(index, VECTOR_STORE_PATH)

def embed_texts(texts):
    return model.encode(texts, convert_to_numpy=True)

def add_text_chunks(index, chunks):
    embeddings = embed_texts(chunks)
    index.add(np.array(embeddings, dtype="float32"))
    save_index(index)
