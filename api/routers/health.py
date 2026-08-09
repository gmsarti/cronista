from typing import Annotated

from fastapi import APIRouter, Depends

from api.config import Settings, get_settings
from api.schemas.world import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthOut:
    return HealthOut(status="ok", app=settings.app_name, version=settings.app_version)
