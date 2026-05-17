import asyncio
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.domain import User
from app.repositories.base import UserRepository

async def test():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        u = User(email='test2@example.com', password_hash='hash')
        try:
            res = await repo.create(u)
            print('Success:', res.user_id)
        except Exception as e:
            print('Error:', repr(e))

asyncio.run(test())
