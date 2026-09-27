from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions

class LocalVectorMemory:
    """Zero-cost embedded vector memory running directly on local disk."""
    def __init__(self, persist_dir: str = "./.memory_chroma"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="workspace_knowledge",
            embedding_function=self.emb_fn
        )

    def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any] = None):
        """Index a document chunk mathematically in under 10ms."""
        self.collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}]
        )

    def search_context(self, query: str, n_results: int = 3) -> List[str]:
        """Perform semantic similarity search for task context."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        docs = results.get("documents", [[]])[0]
        return docs
