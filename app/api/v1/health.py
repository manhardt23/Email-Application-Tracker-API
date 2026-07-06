from fastapi import APIRouter
from starlette.requests import Request

from app.middleware.rate_limit import PUBLIC_LIMIT, get_client_ip, limiter

router = APIRouter()


@router.get("/health")
@limiter.limit(PUBLIC_LIMIT, key_func=get_client_ip, override_defaults=True)
def health_check(request: Request):
    return {"status": "ok"}
