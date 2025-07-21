from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(tags=["CDN"])

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