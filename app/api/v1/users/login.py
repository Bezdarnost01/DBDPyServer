import logging
from fastapi import APIRouter

router = APIRouter(tags=["Users"])

@router.post("/test_user")
async def test_user(login: str,
                    password: int):
    logging.info(f"Попытка добавить нового юзера {login} {password}")