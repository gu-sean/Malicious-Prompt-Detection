from fastapi import FastAPI
from app.api.endpoints import router as api_router
from app.core.database import engine, Base
import uvicorn

app = FastAPI(title="Malicious Prompt Detection API")

@app.on_event("startup")
async def startup():
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(api_router, prefix="/api")

@app.get("/") 
async def root():
    return {"message": "Enterprise Malicious Prompt Detection API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
