import logging
import os
import re
from typing import Annotated
from urllib.parse import urlencode

import httpx
from crud.users import UserManager
from db.users import get_user_session
from fastapi import APIRouter, Depends, HTTPException, Request
from schemas.config import settings
from schemas.users import UserCreate
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger("steam-auth")

router = APIRouter(prefix=settings.api_prefix, tags=["Users"])

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_ID_RE = re.compile(r"https?://steamcommunity\.com/openid/id/(\d+)")
BASE_URL = "https://dbdclub.live"


def _return_to() -> str:
    """Функция `_return_to` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        str: Результат выполнения функции.
    """

    return f"{BASE_URL}{settings.api_prefix}/auth/provider/steam/launcher-callback"


def _realm() -> str:
    """Функция `_realm` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        str: Результат выполнения функции.
    """

    return BASE_URL

STEAM_XML_PROFILE = "https://steamcommunity.com/profiles/{steam_id}/?xml=1"

async def fetch_profile(steam_id: str) -> tuple[str | None, str | None]:
    """Функция `fetch_profile` выполняет прикладную задачу приложения.
    
    Параметры:
        steam_id (str): Идентификатор steam.
    
    Возвращает:
        tuple[str | None, str | None]: Результат выполнения функции.
    """
    # 1) WebAPI
    api_key = (
        getattr(settings, "steam_api_key", None)
        or getattr(settings, "STEAM_API_KEY", None)
        or os.getenv("STEAM_API_KEY")
    )

    if api_key and re.fullmatch(r"[0-9A-Fa-f]{32}", api_key):
        url = (
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
            f"?key={api_key}&steamids={steam_id}"
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, headers={"Accept": "application/json"})
            if r.status_code == 200:
                js = r.json()
                players = js.get("response", {}).get("players", [])
                if players:
                    p = players[0]
                    name = p.get("personaname")
                    avatar = p.get("avatarfull") or p.get("avatar")
                    if name or avatar:
                        return name, avatar
                else:
                    log.warning("WebAPI empty players for %s", steam_id)
            else:
                log.error("WebAPI %s: %s", r.status_code, r.text[:300])
        except Exception as e:
            log.exception("WebAPI request failed: %s", e)
    elif not api_key:
        log.warning("STEAM_API_KEY not set; using XML fallback")
    else:
        log.warning("STEAM_API_KEY looks invalid; using XML fallback")

    # 2) XML фолбэк (публичный профиль)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(STEAM_XML_PROFILE.format(steam_id=steam_id), headers={"Accept": "application/xml"})
        if r.status_code == 200 and "<steamID>" in r.text:
            # простенький парс без зависимостей
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.text)
            name = (root.findtext("steamID") or None)
            avatar = (root.findtext("avatarFull") or root.findtext("avatarMedium") or root.findtext("avatarIcon") or None)
            return name, avatar
        log.warning("XML profile not accessible for %s (status %s)", steam_id, r.status_code)
    except Exception as e:
        log.exception("XML fallback failed: %s", e)

    return None, None

@router.get("/auth/provider/steam/launcher-url")
async def launcher_login_url():
    """Функция `launcher_login_url` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.return_to": _return_to(),
        "openid.realm": _realm(),
    }
    return {"auth_url": f"{STEAM_OPENID_ENDPOINT}?{urlencode(params)}"}

@router.get("/auth/provider/steam/launcher-callback")
async def launcher_callback(
    request: Request,
    db_users: Annotated[AsyncSession, Depends(get_user_session)],
):
    """Функция `launcher_callback` выполняет прикладную задачу приложения.
    
    Параметры:
        request (Request): Входящий HTTP-запрос.
        db_users (Annotated[AsyncSession, Depends(get_user_session)]): Подключение к базе данных.
    
    Возвращает:
        Any: Результат выполнения функции.
    """

    qp = dict(request.query_params)
    if not qp:
        raise HTTPException(status_code=400, detail="No OpenID params")

    verify_payload = {k: v for k, v in qp.items() if k.startswith("openid.")}
    verify_payload["openid.mode"] = "check_authentication"

    async with httpx.AsyncClient(timeout=10) as client:
        ver = await client.post(STEAM_OPENID_ENDPOINT, data=verify_payload)
        if ver.status_code != 200 or "is_valid:true" not in ver.text:
            raise HTTPException(status_code=401, detail="OpenID assertion invalid")

    claimed = qp.get("openid.claimed_id", "")
    m = STEAM_ID_RE.match(claimed)
    if not m:
        raise HTTPException(status_code=400, detail="Bad claimed_id")
    steam_id = m.group(1)

    name, avatar = await fetch_profile(steam_id)

    # 5) Создаём/получаем пользователя в твоей БД (создание — только тут, в лаунчере)
    user = await UserManager.get_user(db_users, steam_id=steam_id)
    first = False
    if user is None:
        user_in = UserCreate(steam_id=steam_id)
        user = await UserManager.create_user(db_users, user_in=user_in)
        # на случай, если create_user у тебя возвращает None
        if user is None:
            user = await UserManager.get_user(db_users, steam_id=steam_id)
        first = True

    if user is None:
        raise HTTPException(status_code=500, detail="User creation failed")

    if getattr(user, "is_banned", False):
        raise HTTPException(status_code=401, detail="You`re banned")

    await UserManager.update_last_login(db_users, steam_id=steam_id)
    try:
        if first and getattr(user, "is_first_login", True):
            # если есть специализированный метод — используй его
            user.is_first_login = False
    except AttributeError:
        # если метода нет — можно просто пропустить или сделать общий update в своём CRUD
        pass

    # 7) Возвращаем ЧИСТЫЕ данные для лаунчера (без куки/токенов)
    return {
        "steam_id": str(steam_id),
        "user_id": user.user_id,       # твой cloud_id
        "name": name,
        "avatar": avatar,
        "is_first_login": bool(not getattr(user, "is_first_login", False) if first else getattr(user, "is_first_login", False)),
    }
