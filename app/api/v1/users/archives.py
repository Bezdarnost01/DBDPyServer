"""Маршруты архивов, возвращающие заглушечные данные для клиента."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from schemas.config import settings

router = APIRouter(prefix=settings.api_prefix, tags=["Archives"])


@router.get("/archives/stories/get/activeNode")
async def get_active_node() -> dict[str, Any]:
    """Функция `get_active_node` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        dict[str, Any]: Результат выполнения функции.
    """

    return {
        "activeNode": [
            {
                "status": "open",
                "nodeTreeCoordinate": {
                    "level": 0,
                    "nodeId": "nodeSurvivorTask01",
                    "storyId": "Tome01",
                },
                "nodeType": "quest:task",
                "coordinates": {
                    "x": 20,
                    "y": 4.615384615384615,
                },
                "neighbors": [
                    "nodeSurvivorChallenge01",
                    "nodeStart",
                ],
                "clientInfoId": "Repair",
                "objectives": [
                    {
                        "objectiveId": "RepairPerc",
                        "conditions": [
                            {
                                "key": "role",
                                "value": ["survivor"],
                            }
                        ],
                        "questEvent": [
                            {
                                "questEventId": "QuestEvent.Repair",
                                "repetition": 1,
                                "parameters": "instigator:me",
                                "operation": ">=",
                            }
                        ],
                        "neededProgression": 200,
                        "incrementWithEventRepetitions": True,
                        "isCommunityObjective": False,
                        "currentProgress": 0,
                    }
                ],
                "rewards": [
                    {
                        "amount": 3,
                        "id": "star",
                        "type": "progressionDbD",
                    },
                    {
                        "amount": 15000,
                        "id": "Bloodpoints",
                        "type": "currency",
                    },
                ],
            }
        ],
        "claimableActiveNodes": [],
        "survivorActiveNode": {
            "level": 0,
            "nodeId": "nodeSurvivorTask01",
            "storyId": "Tome01",
        },
    }


@router.post("/archives/rewards/claim-old-tracks")
async def get_active_rewards() -> dict[str, list[Any]]:
    """Функция `get_active_rewards` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        dict[str, list[Any]]: Результат выполнения функции.
    """

    return {"rewards": []}


@router.get("/archives/stories/get/storyIds")
async def get_stories_ids() -> dict[str, Any]:
    """Функция `get_stories_ids` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        dict[str, Any]: Результат выполнения функции.
    """

    return {
        "openStories": ["Tome02", "Tome01"],
        "storiesStatus": [
            {
                "id": "Tome02",
                "levelStatus": [
                    {
                        "status": "open",
                        "hasUnseenContent": True,
                    },
                    {
                        "status": "locked",
                    },
                    {
                        "status": "locked",
                    },
                    {
                        "status": "locked",
                    },
                ],
            },
            {
                "id": "Tome01",
                "levelStatus": [
                    {
                        "status": "open",
                        "hasUnseenContent": True,
                    },
                    {
                        "status": "locked",
                    },
                    {
                        "status": "locked",
                    },
                    {
                        "status": "locked",
                    },
                ],
            },
        ],
    }


@router.get("/feature/status/archives")
async def archives() -> dict[str, str]:
    """Функция `archives` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        dict[str, str]: Результат выполнения функции.
    """

    return {"status": "on", "feature": "archives"}


@router.get("/archives/rewards/raw-tier")
async def raw_tier() -> dict[str, int]:
    """Функция `raw_tier` выполняет прикладную задачу приложения.
    
    Параметры:
        Отсутствуют.
    
    Возвращает:
        dict[str, int]: Результат выполнения функции.
    """

    return {"tier": 5, "starProgression": 44}


@router.get("/archives/rewards/get-popup-status")
async def get_popup_status(
    archiveId: Annotated[str, Query(alias="archiveId")],
) -> dict[str, bool]:
    """Функция `get_popup_status` выполняет прикладную задачу приложения.
    
    Параметры:
        archiveId (Annotated[str, Query(alias="archiveId")]): Идентификатор архива.
    
    Возвращает:
        dict[str, bool]: Результат выполнения функции.
    """

    return {
        "hasSeenEndPopup": True,
        "hasSeenStartPopup": True,
    }


@router.get("/archives/stories/get/story")
async def get_story(
    storyId: Annotated[str, Query(alias="storyId")],
) -> dict[str, Any]:
    """Функция `get_story` выполняет прикладную задачу приложения.
    
    Параметры:
        storyId (Annotated[str, Query(alias="storyId")]): Идентификатор сюжета.
    
    Возвращает:
        dict[str, Any]: Результат выполнения функции.
    """

    data = {
        "Tome01": {
            "listOfNodes": [
                {
                    "nodeTreeCoordinate": {
                        "storyId": "Tome01",
                        "level": 0,
                        "nodeId": "nodeStart",
                    },
                    "status": "completed",
                },
                {
                    "nodeTreeCoordinate": {
                        "storyId": "Tome01",
                        "level": 0,
                        "nodeId": "node_L1_02",
                    },
                    "status": "open",
                },
                {
                    "nodeTreeCoordinate": {
                        "storyId": "Tome01",
                        "level": 0,
                        "nodeId": "node_L1_09",
                    },
                    "status": "open",
                },
            ],
            "highestLevelIsNewContent": True,
            "activeNodes": [],
            "hasUnreadJournal": False,
        },
        "Tome02": {
            "listOfNodes": [
                {
                    "nodeTreeCoordinate": {
                        "storyId": "Tome02",
                        "level": 0,
                        "nodeId": "nodeStart",
                    },
                    "status": "completed",
                },
                {
                    "nodeTreeCoordinate": {
                        "storyId": "Tome02",
                        "level": 0,
                        "nodeId": "node_L1_02",
                    },
                    "status": "open",
                },
                {
                    "nodeTreeCoordinate": {
                        "storyId": "Tome02",
                        "level": 0,
                        "nodeId": "node_L1_09",
                    },
                    "status": "open",
                },
            ],
            "highestLevelIsNewContent": True,
            "activeNodes": [],
            "hasUnreadJournal": False,
        },
    }
    return data.get(storyId, {})


@router.get("/archives/journal/getjournal")
async def get_journal(
    storyId: Annotated[str, Query(alias="storyId")],
) -> dict[str, Any]:
    """Функция `get_journal` выполняет прикладную задачу приложения.
    
    Параметры:
        storyId (Annotated[str, Query(alias="storyId")]): Идентификатор сюжета.
    
    Возвращает:
        dict[str, Any]: Результат выполнения функции.
    """

    data = {
        "Tome01": {
            "unseenContent": False,
            "vignettes": [
                {
                    "vignetteId": "Tome01_Alchemist",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome01_Claudette",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome01_Entity",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome01_Trapper",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome01_Unknown",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
            ],
        },
        "Tome02": {
            "unseenContent": False,
            "vignettes": [
                {
                    "vignetteId": "Tome02_Doctor",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome02_Jane",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome02_King",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome02_Observer",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome02_Secrets",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
                {
                    "vignetteId": "Tome02_Spirit",
                    "vignette": {
                        "unlockedPages": 100,
                        "lastShownUnlockPages": 0,
                        "readPages": [],
                    },
                },
            ],
        },
    }
    return data.get(storyId, {})
