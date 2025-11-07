# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import chat  # Only import chat for now

app = FastAPI(title="BodhiRAG API", version="1.0.0")

# CORS for web/mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only chat router for now
app.include_router(chat.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "BodhiRAG API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "BodhiRAG API"}