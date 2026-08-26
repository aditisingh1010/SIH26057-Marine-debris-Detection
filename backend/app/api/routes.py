from fastapi import APIRouter, Request

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    inference = getattr(request.app.state, "inference", None)
    loaded = bool(inference and getattr(inference, "loaded", False))
    return {
        "status": "ok",
        "service": settings.service_name,
        "model_loaded": loaded,
        "model_path": str(settings.model_path.name),
    }
