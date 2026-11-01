import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    lm_studio_connected: bool
    loaded_models: list[str] = []
    error: str | None = None


@router.get("/health", response_model=HealthResponse)
async def check_health() -> HealthResponse:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.lm_studio_url.rstrip('/')}/models")
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                models = [m.get("id") for m in data if m.get("id")]
                return HealthResponse(
                    status="ok",
                    lm_studio_connected=True,
                    loaded_models=models,
                )
            return HealthResponse(
                status="degraded",
                lm_studio_connected=False,
                loaded_models=[],
                error=f"LM Studio returned status {resp.status_code}",
            )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            lm_studio_connected=False,
            loaded_models=[],
            error=str(e),
        )


@router.get("/models")
async def list_models() -> dict[str, list[str]]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.lm_studio_url.rstrip('/')}/models")
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                models = [m.get("id") for m in data if m.get("id")]
                return {"models": models}
    except Exception:
        pass
    return {"models": []}
