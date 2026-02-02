
import asyncio
from homelab.rag.rag_indexer import rag_indexer

async def verify_rag():
    print("[Verify] Testing RAG Indexer...")
    
    # 1. Test Embedding & Indexing
    import uuid
    test_id = str(uuid.uuid4())
    test_text = "The quick brown fox jumps over the lazy dog."
    
    print(f"[Verify] Indexing: '{test_text}'")
    await rag_indexer.index_narrative(
        narrative_id=test_id,
        narrative_text=test_text,
        incident_id="verification",
        metadata={"source": "verification_script"},
    )
    
    # 2. Test Search
    query = "brown fox"
    print(f"[Verify] Searching for: '{query}'")
    
    results = await rag_indexer.search_narratives(query, limit=1)
    
    if results:
        print("[Verify] Search Result:")
        print(results[0])
        print("[Verify] RAG Stack: SUCCESS")
    else:
        print("[Verify] RAG Stack: FAILED (No results found)")

if __name__ == "__main__":
    asyncio.run(verify_rag())
