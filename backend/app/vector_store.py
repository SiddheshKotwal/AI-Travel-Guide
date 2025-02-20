import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class FAISSStore:
    def __init__(self, embedding_dim: int = 384):
        """
        Initialize the FAISS index using a flat L2 index and load the SentenceTransformer model.
        """
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.texts = []
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def add_text(self, text: str):
        embedding = self.model.encode([text])
        embedding_np = np.array(embedding, dtype=np.float32)
        self.index.add(embedding_np)
        self.texts.append(text)
    
    def search(self, query: str, top_k: int = 1):
        query_embedding = self.model.encode([query])
        query_np = np.array(query_embedding, dtype=np.float32)
        distances, indices = self.index.search(query_np, top_k)
        results = [self.texts[i] for i in indices[0] if i < len(self.texts)]
        return results

# Global FAISS store instance for simplicity.
faiss_store = FAISSStore()
