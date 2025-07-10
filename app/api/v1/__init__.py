from .users.login import router as login_router
from .services.server_status import router as server_status_router
from .api_utils.utils import router as utils_router

routers = [login_router, server_status_router, utils_router]