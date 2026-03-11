"""ChromaDB memory service — persistent semantic memory for ARIA."""
import uuid

from ..config import settings
from ..logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Manages ARIA's persistent vector memory using ChromaDB."""

    def __init__(self):
        self._client = None
        self._collection = None

    def _ensure_initialized(self):
        """Lazy-init ChromaDB client and collection."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
                from chromadb.utils import embedding_functions
                from ..llm import get_embeddings

                # Get the LangChain embedding model
                lc_embeddings = get_embeddings()
                
                # Wrap LangChain embeddings for ChromaDB
                class LangChainEmbeddingFunction(embedding_functions.EmbeddingFunction):
                    def __init__(self, lc_emb):
                        self.lc_emb = lc_emb
                        
                    def __call__(self, input: list[str]) -> list[list[float]]:
                        return self.lc_emb.embed_documents(input)
                        
                embedding_fn = LangChainEmbeddingFunction(lc_embeddings)

                self._client = chromadb.Client(ChromaSettings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=settings.chroma_persist_dir,
                    anonymized_telemetry=False,
                ))
            except Exception:
                # Fallback: try newer ChromaDB API
                import chromadb
                from ..llm import get_embeddings
                
                lc_embeddings = get_embeddings()
                class LangChainEmbeddingFunction:
                    def __init__(self, lc_emb):
                        self.lc_emb = lc_emb
                    def __call__(self, input: list[str]) -> list[list[float]]:
                        return self.lc_emb.embed_documents(input)
                        
                embedding_fn = LangChainEmbeddingFunction(lc_embeddings)
                
                self._client = chromadb.PersistentClient(
                    path=settings.chroma_persist_dir
                )

            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection,
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )

    async def store(
        self,
        text: str,
        run_id: str,
        source: str = "web_search",
        goal: str = "",
        importance: float = 0.5,
    ) -> str:
        """Store a text chunk in memory. Returns chunk ID."""
        self._ensure_initialized()
        chunk_id = str(uuid.uuid4())

        # Split long text into chunks of ~500 chars
        chunks = self._chunk_text(text, max_chars=800)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            cid = f"{chunk_id}_{i}" if len(chunks) > 1 else chunk_id
            ids.append(cid)
            documents.append(chunk)
            metadatas.append({
                "run_id": run_id,
                "source": source,
                "goal": goal,
                "importance": importance,
                "chunk_index": i,
            })

        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        return chunk_id

    async def retrieve(
        self,
        query: str,
        n_results: int = 5,
        min_importance: float = 0.3,
    ) -> list[dict]:
        """Semantic search for relevant memories."""
        self._ensure_initialized()

        if self._collection.count() == 0:
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, self._collection.count()),
                where={"importance": {"$gte": min_importance}} if self._collection.count() > 0 else None,
            )
        except Exception:
            # Fallback without filter
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, self._collection.count()),
            )

        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                
                # Filter out low-relevance memories (distance > 0.8)
                relevance = 1 - distance
                if relevance < min_importance:
                    continue
                    
                memories.append({
                    "id": results["ids"][0][i],
                    "text": doc,
                    "metadata": meta,
                    "relevance": relevance,  # Convert distance to similarity
                })

        return memories

    async def forget(self, chunk_id: str):
        """Delete a specific memory chunk."""
        self._ensure_initialized()
        try:
            self._collection.delete(ids=[chunk_id])
        except Exception as e:
            logger.warning("Failed to delete memory chunk %s: %s", chunk_id, e)

    async def forget_by_run(self, run_id: str):
        """Delete all memories from a specific run."""
        self._ensure_initialized()
        try:
            self._collection.delete(where={"run_id": run_id})
        except Exception as e:
            logger.warning("Failed to delete memories for run %s: %s", run_id, e)

    async def list_all(self, limit: int = 100) -> list[dict]:
        """List all memory chunks."""
        self._ensure_initialized()

        if self._collection.count() == 0:
            return []

        results = self._collection.get(
            limit=limit,
            include=["documents", "metadatas"],
        )

        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                memories.append({
                    "id": results["ids"][i],
                    "text": doc,
                    "metadata": meta,
                })

        return memories

    async def count(self) -> int:
        """Return total number of stored memories."""
        self._ensure_initialized()
        return self._collection.count()

    def _chunk_text(self, text: str, max_chars: int = 1000) -> list[str]:
        """Split text into chunks with overlap for better embedding context."""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=max_chars,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            return text_splitter.split_text(text)
        except ImportError:
            # Fallback to simple chunking if langchain is somehow missing
            if len(text) <= max_chars:
                return [text]

            chunks = []
            paragraphs = text.split("\n\n")
            current = ""

            for para in paragraphs:
                if len(current) + len(para) + 2 > max_chars:
                    if current:
                        chunks.append(current.strip())
                    current = para
                else:
                    current = f"{current}\n\n{para}" if current else para

            if current.strip():
                chunks.append(current.strip())

            return chunks if chunks else [text[:max_chars]]


# Singleton instance
memory_service = MemoryService()
