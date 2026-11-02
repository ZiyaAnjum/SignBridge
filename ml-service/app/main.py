"""SignBridge ML & Recognition Service Entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import health, samples, websocket

app = FastAPI(
    title="SignBridge ML Service",
    description="Live ISL landmark recognition, sample collection, and translation API.",
    version="0.1.0",
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration
app.include_router(health.router)
app.include_router(samples.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "service": "SignBridge ML Service",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "samples": "/samples/counts",
        "ws_landmarks": "/ws/landmarks",
    }
