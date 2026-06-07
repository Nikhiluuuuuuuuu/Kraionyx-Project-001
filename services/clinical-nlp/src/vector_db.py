import faiss
import numpy as np

class MockPatientHistoryDB:
    """
    Mock Vector Database for Patient History using FAISS.
    Simulates RAG by storing and retrieving past clinical notes or conditions.
    """
    def __init__(self, embedding_dim=1024):
        self.embedding_dim = embedding_dim
        # Using L2 distance for similarity
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.documents = []
        self.patient_map = {} # Maps patient_id to their document indices
        self.max_patients = 1000 # LRU capacity
        
    def _mock_embed(self, text: str) -> np.ndarray:
        # Mock BGE-m3 embedding logic (which typically uses 1024 dimensions)
        np.random.seed(abs(hash(text)) % (2**32))
        vec = np.random.randn(self.embedding_dim).astype('float32')
        faiss.normalize_L2(vec.reshape(1, -1))
        return vec.reshape(1, -1)
        
    def add_history(self, patient_id: str, document: str):
        vec = self._mock_embed(document)
        idx = len(self.documents)
        self.documents.append(document)
        self.index.add(vec)
        
        if patient_id in self.patient_map:
            # Move to end to mark as recently used
            docs = self.patient_map.pop(patient_id)
            self.patient_map[patient_id] = docs
        else:
            self.patient_map[patient_id] = []
            
            # LRU eviction
            if len(self.patient_map) > self.max_patients:
                # Remove oldest patient from map
                oldest_patient = next(iter(self.patient_map))
                del self.patient_map[oldest_patient]
                # Note: For a true mock, we'd also clean up self.documents and self.index,
                # but to avoid complex index rebuilding in this mock, we just drop the patient reference.
                
        self.patient_map[patient_id].append(idx)
        
    def retrieve_history(self, patient_id: str, query: str, top_k: int = 2) -> list[str]:
        if patient_id not in self.patient_map or not self.patient_map[patient_id]:
            return []
            
        # Update LRU
        docs = self.patient_map.pop(patient_id)
        self.patient_map[patient_id] = docs
            
        query_vec = self._mock_embed(query)
        # For simplicity in mock: just return the patient's past documents 
        # In actual FAISS, we'd search within the subset or filter post-search
        # Here we'll do a global search and filter by patient
        D, I = self.index.search(query_vec, self.index.ntotal)
        
        results = []
        for idx in I[0]:
            if idx in self.patient_map.get(patient_id, []) and idx != -1:
                results.append(self.documents[idx])
                if len(results) >= top_k:
                    break
        return results
