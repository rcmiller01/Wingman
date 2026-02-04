#!/usr/bin/env python3
"""Quick check of audit chain state."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from homelab.storage.models import ActionHistory


async def check():
    db_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(db_url, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # Total count
        cnt = await session.execute(select(func.count()).select_from(ActionHistory))
        total = cnt.scalar()
        print(f"Total entries: {total}")
        
        # Sequence distribution
        q = select(
            ActionHistory.sequence_num, 
            func.count().label("cnt")
        ).group_by(ActionHistory.sequence_num).order_by(ActionHistory.sequence_num)
        result = await session.execute(q)
        print("\nSequence distribution:")
        for row in result:
            print(f"  seq={row.sequence_num}: {row.cnt} entries")
        
        # Show last 5 with hash chain
        q2 = select(ActionHistory).where(
            ActionHistory.sequence_num.isnot(None)
        ).order_by(ActionHistory.sequence_num.desc()).limit(5)
        result2 = await session.execute(q2)
        print("\nLast 5 entries with sequence_num:")
        for entry in result2.scalars():
            print(f"  seq={entry.sequence_num}, hash={entry.entry_hash[:12] if entry.entry_hash else 'None'}, "
                  f"prev={entry.prev_hash[:12] if entry.prev_hash else 'None'}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
