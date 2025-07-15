from .users.login import router as login_router
from .users.profile import router as profile_router
from .users.reward import router as reward_router
from .users.store import router as store_router
from .users.archives import router as archives_router
from .users.rtm import router as rtm_router
from .services.server_status import router as server_status_router
from .api_utils.utils import router as utils_router
from .party.party import router as party_router

routers = [login_router, server_status_router, utils_router, profile_router,
           reward_router, store_router, archives_router, rtm_router, party_router]