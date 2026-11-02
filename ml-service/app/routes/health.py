"""Health check endpoints."""
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.protocol import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def check_health() -> HealthResponse:
    """Return runtime service health, device configuration, and model state."""
    return HealthResponse(
        status="ok",
        service="signbridge-ml-service",
        version="0.1.0",
        device=settings.DEVICE,
        model_loaded=False,
    )

