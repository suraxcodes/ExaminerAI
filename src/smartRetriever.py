from sentence_transformers import SentenceTransformer, util
import torch

class SmartRetriever:
    def __init__(self):
        # Load the lightweight model (approx 80MB)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chunk_embeddings = None
        self.chunks = []

    def prepare_index(self, chunks):
        """Convert all document chunks into vectors (embeddings)"""
        if not chunks:
            print("⚠ Warning: No chunks provided for indexing. SmartRetriever will return empty results.")
            self.chunks = []
            self.chunk_embeddings = None
            return

        self.chunks = chunks
        chunk_texts = [c.content for c in chunks if hasattr(c, 'content')]
        
        if not chunk_texts:
             self.chunk_embeddings = None
             return

        # This converts text into a 384-dimensional numerical map
        self.chunk_embeddings = self.model.encode(chunk_texts, convert_to_tensor=True)
        print(f"✓ Indexed {len(chunks)} chunks for semantic search.")

    def search(self, syllabus_topic, top_k=3):
        """Find the chunks most relevant to a specific syllabus topic"""
        if self.chunk_embeddings is None or not self.chunks:
            return []

        query_embedding = self.model.encode(syllabus_topic, convert_to_tensor=True)
        
        # Calculate Cosine Similarity between query and all chunks
        hits = util.semantic_search(query_embedding, self.chunk_embeddings, top_k=top_k)
        
        # Extract the best matching chunks without mutating them
        results = []
        for hit in hits[0]:
            chunk_idx = hit['corpus_id']
            if chunk_idx < len(self.chunks):
                results.append({
                    "chunk": self.chunks[chunk_idx],
                    "relevance_score": float(hit['score'])
                })
            
        return results
