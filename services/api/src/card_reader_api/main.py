from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from card_reader_api.infrastructure.db import initialize_database
from card_reader_api.infrastructure.logging_utils import configure_logging
from card_reader_api.interfaces.http.api import build_api_router
from card_reader_api.settings import settings


app = FastAPI(title="Card Reader API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_dev else settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(build_api_router())


@app.on_event("startup")
def on_startup() -> None:
    configure_logging()
    initialize_database()
