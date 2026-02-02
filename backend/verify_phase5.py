
import asyncio
from homelab.rag.vector_store import vector_store

async def verify_rag():
    print("[Verify] Testing Vector Store...")
    
    # 1. Test Embedding & Indexing
    import uuid
    test_id = str(uuid.uuid4())
    test_text = "The quick brown fox jumps over the lazy dog."
    
    print(f"[Verify] Indexing: '{test_text}'")
    await vector_store.index_narrative(
        narrative_id=test_id,
        text=test_text,
        meta={"source": "verification_script"}
    )
    
    # 2. Test Search
    query = "brown fox"
    print(f"[Verify] Searching for: '{query}'")
    
    # DEBUG: Inspect client
    print(f"[Verify] Client methods: {dir(vector_store.client)}")
    
    results = await vector_store.search_similar(query, limit=1)
    
    if results:
        print("[Verify] Search Result:")
        print(results[0])
        print("[Verify] RAG Stack: SUCCESS")
    else:
        print("[Verify] RAG Stack: FAILED (No results found)")

if __name__ == "__main__":
    asyncio.run(verify_rag())
