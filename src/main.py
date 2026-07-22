"""ContentForge - AI-powered content generation platform."""
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="ContentForge", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "ContentForge API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
