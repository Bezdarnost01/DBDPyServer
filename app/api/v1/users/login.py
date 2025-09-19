import logging
from fastapi import APIRouter

router = APIRouter(tags=["Users"])

@router.post("/test_user")
async def test_user(login: str,
                    password: int):
    """Log the user test endpoint invocation.

    Args:
        login (str): Unique identifier of the user initiating the request.
        password (int): Numeric password provided for the authentication attempt.

    Returns:
        None: This endpoint only records the request for auditing purposes.
    """
    logging.info(f"Попытка добавить нового юзера {login} {password}")
