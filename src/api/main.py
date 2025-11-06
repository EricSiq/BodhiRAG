#BodhiRAG-main\src\api\main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
from .routes import chat, graph, analytics

app = FastAPI(title="BodhiRAG API", version="1.0.0")

# CORS for web/mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Initialize rate limiter
    redis_connection = redis.from_url("redis://localhost:6379", encoding="utf-8")
    await FastAPILimiter.init(redis_connection)

# Include routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "BodhiRAG API", "status": "healthy"}