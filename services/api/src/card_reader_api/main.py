from fastapi import FastAPI

from card_reader_api.infrastructure.db import initialize_database
from card_reader_api.interfaces.http.api import build_api_router


app = FastAPI(title="Card Reader API", version="0.1.0")
app.include_router(build_api_router())


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()