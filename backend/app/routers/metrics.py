from typing import Annotated

from fastapi import APIRouter, Depends

from app.observability import metrics
from app.routers.auth import UserOut, current_user

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
def get_metrics(_: Annotated[UserOut, Depends(current_user)]) -> dict:
    return metrics.snapshot()
