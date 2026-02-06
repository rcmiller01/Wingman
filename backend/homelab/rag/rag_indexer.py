"""RAG Indexer - indexes documents into Qdrant vector store."""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from datetime import datetime
import uuid

from homelab.config import get_settings
from homelab.llm.providers import llm_manager, EmbeddingBlockedError


settings = get_settings()

# Collection names
NARRATIVES_COLLECTION = "incident_narratives"
SUMMARIES_COLLECTION = "log_summaries"

# Allow destructive operations (recreate collections)
ALLOW_DESTRUCTIVE_ACTIONS = os.environ.get("ALLOW_DESTRUCTIVE_ACTIONS", "false").lower() == "true"


class RAGIndexer:
    """Indexes documents into Qdrant for RAG retrieval."""

    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)

    def _get_target_dimension(self) -> int:
        """Get the target embedding dimension from LLM manager."""
        return llm_manager.get_embedding_dimension()

    def ensure_collections(self):
        """Ensure required collections exist."""
        try:
            dim = self._get_target_dimension()
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if NARRATIVES_COLLECTION not in collection_names:
                self.client.create_collection(
                    collection_name=NARRATIVES_COLLECTION,
                    vectors_config=VectorParams(
                        size=dim,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"[RAGIndexer] Created collection: {NARRATIVES_COLLECTION} (dim={dim})")

            if SUMMARIES_COLLECTION not in collection_names:
                self.client.create_collection(
                    collection_name=SUMMARIES_COLLECTION,
                    vectors_config=VectorParams(
                        size=dim,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"[RAGIndexer] Created collection: {SUMMARIES_COLLECTION} (dim={dim})")

        except Exception as e:
            print(f"[RAGIndexer] Error ensuring collections: {e}")

    def get_collection_info(self) -> dict:
        """Get info about all managed collections including vector sizes."""
        result = {
            "collections": [],
            "consistent": True,
            "dimensions": set(),
        }
        try:
            for name in [NARRATIVES_COLLECTION, SUMMARIES_COLLECTION]:
                try:
                    info = self.client.get_collection(name)
                    vector_size = info.config.params.vectors.size
                    points_count = info.points_count
                    result["collections"].append({
                        "name": name,
                        "vector_size": vector_size,
                        "points_count": points_count,
                        "exists": True,
                    })
                    result["dimensions"].add(vector_size)
                except Exception:
                    result["collections"].append({
                        "name": name,
                        "vector_size": None,
                        "points_count": 0,
                        "exists": False,
                    })

            # Check consistency
            existing_dims = [c["vector_size"] for c in result["collections"] if c["exists"]]
            result["consistent"] = len(set(existing_dims)) <= 1
            result["dimensions"] = list(result["dimensions"])

        except Exception as e:
            result["error"] = str(e)

        return result

    def get_existing_dimension(self) -> tuple[int | None, bool]:
        """Get the vector dimension from existing collections, if any.

        Returns:
            Tuple of (dimension, is_consistent).
            - dimension: The vector size if any collection exists, None otherwise
            - is_consistent: True if all existing collections have the same dimension
        """
        dimensions = []
        try:
            for name in [NARRATIVES_COLLECTION, SUMMARIES_COLLECTION]:
                try:
                    info = self.client.get_collection(name)
                    dimensions.append(info.config.params.vectors.size)
                except Exception:
                    continue  # Collection doesn't exist
        except Exception:
            pass

        if not dimensions:
            return None, True  # No collections = consistent (nothing to conflict)

        unique_dims = set(dimensions)
        is_consistent = len(unique_dims) == 1
        # Return the first dimension found (deterministic: narratives before summaries)
        return dimensions[0], is_consistent

    def recreate_collections(self, new_dimension: int) -> dict:
        """Recreate collections with new dimension. DESTRUCTIVE - all data lost."""
        if not ALLOW_DESTRUCTIVE_ACTIONS:
            return {
                "success": False,
                "error": "Destructive actions disabled. Set ALLOW_DESTRUCTIVE_ACTIONS=true to enable.",
            }

        results = {"success": True, "collections": [], "dimension": new_dimension}

        for name in [NARRATIVES_COLLECTION, SUMMARIES_COLLECTION]:
            try:
                # Delete if exists
                try:
                    self.client.delete_collection(name)
                    print(f"[RAGIndexer] Deleted collection: {name}")
                except Exception:
                    pass  # Didn't exist

                # Create with new dimension
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=new_dimension,
                        distance=Distance.COSINE,
                    ),
                )
                results["collections"].append({"name": name, "status": "recreated"})
                print(f"[RAGIndexer] Recreated collection: {name} (dim={new_dimension})")

            except Exception as e:
                results["collections"].append({"name": name, "status": "error", "error": str(e)})
                results["success"] = False

        return results
    
    async def index_narrative(
        self,
        narrative_id: str,
        narrative_text: str,
        incident_id: str,
        metadata: dict | None = None,
    ) -> bool:
        """Index an incident narrative.

        Raises:
            EmbeddingBlockedError: When system is in blocked state.
        """
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
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                    **(metadata or {}),
                },
            )

            self.client.upsert(
                collection_name=NARRATIVES_COLLECTION,
                points=[point],
            )

            print(f"[RAGIndexer] Indexed narrative {narrative_id}")
            return True

        except EmbeddingBlockedError:
            # Re-raise - callers must handle blocked state explicitly
            raise
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
        """Index a log summary.

        Raises:
            EmbeddingBlockedError: When system is in blocked state.
        """
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
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                    **(metadata or {}),
                },
            )

            self.client.upsert(
                collection_name=SUMMARIES_COLLECTION,
                points=[point],
            )

            return True

        except EmbeddingBlockedError:
            # Re-raise - callers must handle blocked state explicitly
            raise
        except Exception as e:
            print(f"[RAGIndexer] Error indexing summary: {e}")
            return False
    
    async def search_narratives(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search for similar incident narratives.

        Raises:
            EmbeddingBlockedError: When system is in blocked state.
        """
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

        except EmbeddingBlockedError:
            raise
        except Exception as e:
            print(f"[RAGIndexer] Search error: {e}")
            return []

    async def search_summaries(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search for similar log summaries.

        Raises:
            EmbeddingBlockedError: When system is in blocked state.
        """
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

        except EmbeddingBlockedError:
            raise
        except Exception as e:
            print(f"[RAGIndexer] Search error: {e}")
            return []
    
    async def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding from configured LLM provider.

        Raises:
            EmbeddingBlockedError: Re-raised to caller when system is blocked.
        """
        try:
            return await llm_manager.embed(text[:4000])  # Limit input size
        except EmbeddingBlockedError:
            # Re-raise blocked state - callers must handle this explicitly
            raise
        except Exception as e:
            print(f"[RAGIndexer] Embedding error: {e}")
            return None


# Singleton
rag_indexer = RAGIndexer()
