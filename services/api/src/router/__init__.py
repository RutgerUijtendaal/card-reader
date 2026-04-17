from fastapi import APIRouter

from controllers.cards_controller import router as cards_router
from controllers.exports_controller import router as exports_router
from controllers.imports_controller import router as imports_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(imports_router, tags=["imports"])
    router.include_router(cards_router, tags=["cards"])
    router.include_router(exports_router, tags=["exports"])
    return router
