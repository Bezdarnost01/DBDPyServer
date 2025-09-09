from pathlib import Path

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import FileResponse
from schemas.config import ValidateChallengeResponse, VersionConfig, settings
from schemas.utils import (
    ClientVersionResponse,
    ContentVersionResponse,
    EacChallengeResponse,
    HealthResponse,
)

router = APIRouter(prefix=settings.api_prefix, tags=["Utils"])

@router.get("/healthcheck", response_model=HealthResponse)
async def healthcheck():
    return {"health": "Alive"}

@router.get("/version", response_model=VersionConfig)
async def get_version():
    return settings.version

@router.get("/utils/contentVersion/version", response_model=ContentVersionResponse)
async def content_version():
    return settings.content_version

@router.post("/extensions/eac/generateChallenge", response_model=EacChallengeResponse)
async def generate_eac_challenge():
    return {"challenge": settings.eac_challenge}

@router.post("/extensions/eac/validateChallengeResponse", response_model=ValidateChallengeResponse)
async def validateChallenge():
    return settings.validate_challenge

@router.get("/config", response_class=FileResponse)
async def get_config_file():
    config_path = Path("../assets/config.json").resolve()
    if not config_path.exists():
        msg = f"File at path {config_path} does not exist."
        raise RuntimeError(msg)
    return FileResponse(str(config_path), media_type="application/json")

@router.post("/clientVersion/check", response_model=ClientVersionResponse)
async def client_version_check():
    return {"isValid": True}

@router.post("/extensions/store/getAvailableBundles")
async def get_available_bundles():
    config_path = Path("../assets/bundles.json").resolve()
    if not config_path.exists():
        msg = f"File at path {config_path} does not exist."
        raise RuntimeError(msg)
    return FileResponse(str(config_path), media_type="application/json")

@router.post("/extensions/wallet/needMigration")
async def need_migration(request: Request):
    try:
        body = await request.json()
        return body["data"]
    except Exception:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.post("/extensions/wallet/migrateCurrencies")
async def migrate_currencies(request: Request):
    try:
        body = await request.json()
        currency_list = body["data"]["list"]
        return {
            "migrationStatus": True,
            "list": [
                {"migrated": True, "currency": c["currency"], "reason": "NONE"}
                for c in currency_list
            ],
        }
    except Exception:
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
