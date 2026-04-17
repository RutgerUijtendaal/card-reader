from fastapi import APIRouter

from card_reader_api.interfaces.http.routes.cards import router as cards_router
from card_reader_api.interfaces.http.routes.exports import router as exports_router
from card_reader_api.interfaces.http.routes.imports import router as imports_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(imports_router, tags=["imports"])
    router.include_router(cards_router, tags=["cards"])
    router.include_router(exports_router, tags=["exports"])
    return router