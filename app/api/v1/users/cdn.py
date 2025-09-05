from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
import json
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Any
from schemas.config import settings

router = APIRouter(tags=["CDN"])

CONFIG = {
    "MATCHMAKING_USE_QUEUE_API": True,
    "GAME_ON_UI_ENABLE_PLATFORM": "ENABLED"
}

@router.get(f"{settings.api_prefix}/config/GAME_ON_UI_ENABLE_PLATFORM/raw")
async def game_on_ui_enable_platform_raw():
    return Response(content="", media_type="application/json")

@router.get(f"{settings.api_prefix}/config/{{key}}")
async def get_config_value(key: str):
    value: Any = CONFIG.get(key)
    if isinstance(value, str):
        return Response(content=json.dumps(value), media_type="application/json")
    else:
        return JSONResponse(content=value)

@router.get("/gameinfo/{json_file}")
async def gameinfo_content(json_file: str):
    if json_file == "catalog.json":
        bin_path = Path("../assets/cdn/catalog.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/specialEvents/{json_file}")
async def specialEvents_content(json_file: str):
    if json_file == "specialEventsContent.json":
        bin_path = Path("../assets/cdn/specialEventsContent.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/bonusPointEvents/{json_file}")
async def bonusPointEvents_content(json_file: str):
    if json_file == "bonusPointEventsContent.json":
        bin_path = Path("../assets/cdn/bonusPointEventsContent.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/news/{json_file}")
async def news_content(json_file: str):
    if json_file == "newsContent.json":
        bin_path = Path("../assets/cdn/newsContent.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/schedule/{json_file}")
async def schedule_content(json_file: str):
    if json_file == "contentSchedule.json":
        bin_path = Path("../assets/cdn/contentSchedule.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/clientData/{key}/content/{version_game}/{json_file}")
async def cdn_content(key: str, version_game: str, json_file: str):
    if json_file == "emblemTunable.json":
        bin_path = Path("../assets/cdn/emblemTunable.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")
    elif json_file == "catalog.json":
        bin_path = Path("../assets/cdn/catalog.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")
    elif json_file == "ranksThresholds.json":
        bin_path = Path("../assets/cdn/ranksThresholds.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")
    elif json_file == "specialEventsContent.json":
        bin_path = Path("../assets/cdn/specialEventsContent.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")
    elif json_file == "GameConfigs.json":
        bin_path = Path("../assets/cdn/GameConfigs.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/clientData/{key}/content/{version_game}/{subfolder}/{json_file}")
async def cdn_content_subfolder(key: str, version_game: str, subfolder: str, json_file: str):
    if subfolder == "archiveRewardData":
        bin_path = Path("../assets/cdn/archiveRewardData.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

    file_path = Path(f"../assets/cdn/{subfolder}/{json_file}").resolve()
    if not file_path.exists():
        raise RuntimeError(f"File at path {file_path} does not exist.")
    if file_path.suffix.lower() == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    return FileResponse(file_path, media_type="application/octet-stream")

@router.get("/clientData/{key}/banners/{json_file}")
async def cdn_banners(key: str, json_file: str):
    if json_file == "featuredPageContent.json":
        bin_path = Path("../assets/cdn/featuredPageContent.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/clientData/{key}/bonusPointEvents/{json_file}")
async def cdn_bonus_point_events(key: str, json_file: str):
    if json_file == "bonusPointEventsContent.json":
        bin_path = Path("../assets/cdn/bonusPointEventsContent.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/clientData/{key}/schedule/{json_file}")
async def cdn_schedule(key: str, json_file: str):
    if json_file == "contentSchedule.json":
        bin_path = Path("../assets/cdn/contentSchedule.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")

@router.get("/clientData/{key}/news/{json_file}")
async def cdn_news(key: str, json_file: str):
    if json_file == "newsContent.json":
        bin_path = Path("../assets/cdn/newsContent.bin").resolve()
        if not bin_path.exists():
            raise RuntimeError(f"File at path {bin_path} does not exist.")
        return FileResponse(bin_path, media_type="application/octet-stream")