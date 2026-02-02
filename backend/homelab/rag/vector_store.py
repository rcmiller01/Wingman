"""Vector Store - Interface for Qdrant RAG operations."""

import time
import httpx
from typing import List, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from homelab.config import get_settings

settings = get_settings()

class VectorStore:
    """Manages embeddings and vector storage in Qdrant."""
    
    def __init__(self):
        # Connect to Qdrant (hostname 'qdrant' in docker-compose, or localhost if running outside)
        # Using environment variable or default
        qdrant_url = settings.qdrant_url
        if "://" in qdrant_url:
            # Parse host and port from URL (simple version)
            parts = qdrant_url.split("://")[-1].split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 6333
            self.client = AsyncQdrantClient(host=host, port=port)
        else:
            self.client = AsyncQdrantClient(url=qdrant_url)
            
        self.ollama_base_url = settings.ollama_host
        self.embedding_model = "nomic-embed-text" 
        self.collection_name = "homelab_narratives"
        # Since __init__ is sync, we can't await. 
        # We'll expect the caller or a startup event to ensure collection, 
        # or just lazily create it on first index/search.
        # For validation simplicity, we'll try to ensure it via a helper run in background,
        # or just let the first operation create it if needed.
        
    async def ensure_collection(self):
        """Create collection if it doesn't exist."""
        try:
             # collection_exists is not always available or consistent, just try get
            await self.client.get_collection(self.collection_name)
        except Exception:
            print(f"[VectorStore] Creating collection {self.collection_name}")
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama."""
        async with httpx.AsyncClient() as client:
            try:
                # Truncate text if too long to avoid context window issues
                # nomic-embed-text usually supports 8192 tokens, but let's be safe
                truncated_text = text[:8000] 
                
                resp = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": truncated_text
                    },
                    timeout=30.0
                )
                if resp.status_code != 200:
                    print(f"[VectorStore] Embedding error: {resp.text}")
                    return []
                
                return resp.json()["embedding"]
            except Exception as e:
                print(f"[VectorStore] Embedding request failed: {e}")
                return []

    async def index_narrative(self, narrative_id: str, text: str, meta: Dict[str, Any]):
        """Index an incident narrative."""
        await self.ensure_collection()
        embedding = await self.get_embedding(text)
        if not embedding:
            return

        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=narrative_id, 
                    vector=embedding,
                    payload={
                        "type": "narrative",
                        "text": text,
                        **meta
                    }
                )
            ]
        )
        print(f"[VectorStore] Indexed narrative {narrative_id}")

    async def index_log_summary(self, summary_id: str, text: str, meta: Dict[str, Any]):
        """Index a log summary."""
        await self.ensure_collection()
        embedding = await self.get_embedding(text)
        if not embedding:
            return

        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=summary_id, 
                    vector=embedding,
                    payload={
                        "type": "log_summary",
                        "text": text,
                        **meta
                    }
                )
            ]
        )
        print(f"[VectorStore] Indexed log summary {summary_id}")

    async def search_similar(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for similar narratives."""
        await self.ensure_collection()
        embedding = await self.get_embedding(query)
        if not embedding:
            return []

        resp = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=limit
        )
        hits = resp.points

        results = []
        for hit in hits:
            results.append({
                "score": hit.score,
                "payload": hit.payload
            })
        return results

# Singleton
vector_store = VectorStore()
