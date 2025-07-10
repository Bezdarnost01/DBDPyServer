from fastapi import APIRouter
from schemas.utils import HealthResponse, ContentVersionResponse, EacChallengeResponse
from schemas.config import settings, VersionConfig, ValidateChallengeResponse

router = APIRouter(prefix=settings.api_prefix, tags=["Utils"])

@router.get("/healthcheck", response_model=HealthResponse)
async def healthcheck():
    return {"health": "Alive"}

@router.get("/version", response_model=VersionConfig)
async def get_version():
    return settings.version

@router.get("/utils/contentVersion/version", response_model=ContentVersionResponse)
async def healthcheck():
    return settings.content_version

@router.post("/extensions/eac/generateChallenge", response_model=EacChallengeResponse)
async def generate_eac_challenge():
    return {"challenge": settings.eac_challenge}

@router.post("/extensions/eac/validateChallengeResponse", response_model=ValidateChallengeResponse)
async def validateChallenge():
    return settings.validate_challenge