import asyncio
import sys
from os.path import dirname, abspath

# Add backend to sys.path
sys.path.insert(0, dirname(abspath(__file__)))

from homelab.storage.database import engine, Base
from homelab.storage import models

async def init_models():
    async with engine.begin() as conn:
        # For a hard reset, we might want to drop all first, 
        # but let's just try creating for now.
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_models())
