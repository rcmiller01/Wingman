"""RAG Indexer - indexes documents into Qdrant vector store."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from datetime import datetime
import uuid

from homelab.config import get_settings
from homelab.llm.providers import llm_manager


settings = get_settings()

# Embedding dimension - matches common embedding models
# nomic-embed-text: 768, text-embedding-3-small: 1536
# We use 768 as default for Ollama compatibility
EMBEDDING_DIMENSION = 768

# Collection names
NARRATIVES_COLLECTION = "incident_narratives"
SUMMARIES_COLLECTION = "log_summaries"


class RAGIndexer:
    """Indexes documents into Qdrant for RAG retrieval."""
    
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Ensure required collections exist."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if NARRATIVES_COLLECTION not in collection_names:
                self.client.create_collection(
                    collection_name=NARRATIVES_COLLECTION,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"[RAGIndexer] Created collection: {NARRATIVES_COLLECTION}")
            
            if SUMMARIES_COLLECTION not in collection_names:
                self.client.create_collection(
                    collection_name=SUMMARIES_COLLECTION,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"[RAGIndexer] Created collection: {SUMMARIES_COLLECTION}")
                
        except Exception as e:
            print(f"[RAGIndexer] Error ensuring collections: {e}")
    
    async def index_narrative(
        self,
        narrative_id: str,
        narrative_text: str,
        incident_id: str,
        metadata: dict | None = None,
    ) -> bool:
        """Index an incident narrative."""
        try:
            embedding = await self._get_embedding(narrative_text)
            if not embedding:
                return False
            
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "narrative_id": narrative_id,
                    "incident_id": incident_id,
                    "text": narrative_text[:2000],  # Store truncated for retrieval
                    "indexed_at": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                },
            )
            
            self.client.upsert(
                collection_name=NARRATIVES_COLLECTION,
                points=[point],
            )
            
            print(f"[RAGIndexer] Indexed narrative {narrative_id}")
            return True
            
        except Exception as e:
            print(f"[RAGIndexer] Error indexing narrative: {e}")
            return False
    
    async def index_log_summary(
        self,
        resource_ref: str,
        summary_text: str,
        time_range: dict,
        metadata: dict | None = None,
    ) -> bool:
        """Index a log summary."""
        try:
            embedding = await self._get_embedding(summary_text)
            if not embedding:
                return False
            
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "resource_ref": resource_ref,
                    "text": summary_text[:2000],
                    "time_range": time_range,
                    "indexed_at": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                },
            )
            
            self.client.upsert(
                collection_name=SUMMARIES_COLLECTION,
                points=[point],
            )
            
            return True
            
        except Exception as e:
            print(f"[RAGIndexer] Error indexing summary: {e}")
            return False
    
    async def search_narratives(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search for similar incident narratives."""
        try:
            embedding = await self._get_embedding(query)
            if not embedding:
                return []
            
            results = self.client.search(
                collection_name=NARRATIVES_COLLECTION,
                query_vector=embedding,
                limit=limit,
            )
            
            return [
                {
                    "score": r.score,
                    "narrative_id": r.payload.get("narrative_id"),
                    "incident_id": r.payload.get("incident_id"),
                    "text": r.payload.get("text"),
                }
                for r in results
            ]
            
        except Exception as e:
            print(f"[RAGIndexer] Search error: {e}")
            return []
    
    async def search_summaries(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search for similar log summaries."""
        try:
            embedding = await self._get_embedding(query)
            if not embedding:
                return []
            
            results = self.client.search(
                collection_name=SUMMARIES_COLLECTION,
                query_vector=embedding,
                limit=limit,
            )
            
            return [
                {
                    "score": r.score,
                    "resource_ref": r.payload.get("resource_ref"),
                    "text": r.payload.get("text"),
                    "time_range": r.payload.get("time_range"),
                }
                for r in results
            ]
            
        except Exception as e:
            print(f"[RAGIndexer] Search error: {e}")
            return []
    
    async def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding from configured LLM provider."""
        try:
            return await llm_manager.embed(text[:4000])  # Limit input size
        except Exception as e:
            print(f"[RAGIndexer] Embedding error: {e}")
            return None


# Singleton
rag_indexer = RAGIndexer()
