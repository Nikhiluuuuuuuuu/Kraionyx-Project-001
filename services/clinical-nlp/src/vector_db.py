import os
import chromadb
from sentence_transformers import SentenceTransformer
import structlog
import hashlib

logger = structlog.get_logger(__name__)

class PatientHistoryDB:
    """
    Vector Database for Patient History using ChromaDB and BAAI/bge-m3 embeddings.
    """
    def __init__(self, persist_directory=None):
        if persist_directory is None:
            persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="patient_history")
        
        logger.info("Loading BAAI/bge-m3 embedding model...")
        try:
            self.encoder = SentenceTransformer("BAAI/bge-m3")
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.encoder = None

    def add_history(self, patient_id: str, document: str):
        if not self.encoder:
            logger.error("Cannot add history: Embedding model not loaded.")
            return

        embedding = self.encoder.encode(document).tolist()
        doc_id = hashlib.sha256(document.encode()).hexdigest()[:16]
        
        self.collection.upsert(
            documents=[document],
            embeddings=[embedding],
            metadatas=[{"patient_id": patient_id}],
            ids=[f"{patient_id}_{doc_id}"]
        )
        logger.debug(f"Added history for patient {patient_id}")
        
    def retrieve_history(self, patient_id: str, query: str, top_k: int = 2) -> list[str]:
        if not self.encoder:
            logger.error("Cannot retrieve history: Embedding model not loaded.")
            return []

        query_embedding = self.encoder.encode(query).tolist()
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"patient_id": patient_id}
            )
            
            if results and "documents" in results and results["documents"]:
                return results["documents"][0]
        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            
        return []
