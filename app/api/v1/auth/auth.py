from fastapi import APIRouter
from schemas.config import settings

router = APIRouter(prefix=settings.api_admin_prefix, tags=["Auth"])

