from .users.login import router as login_router
from .services.server_status import router as server_status_router

routers = [login_router, server_status_router]