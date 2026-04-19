import logging
from collections.abc import AsyncIterator
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from card_reader_api.router import build_api_router
from card_reader_core.database.connection import initialize_database
from card_reader_api.database_migrations import run_migrations_to_head
from card_reader_core.core_logging import configure_logging
from card_reader_api.seeds import run_registered_seeds
from card_reader_core.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    initialize_database()
    run_migrations_to_head()
    try:
        run_registered_seeds(force=False)
    except Exception:
        logger.exception("Seed initialization failed during startup")
    yield


app = FastAPI(title="Card Reader API", version="0.1.7", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_dev else settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(build_api_router())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = str(uuid4())
    logger.exception(
        "Unhandled API exception. request_id=%s method=%s path=%s query=%s",
        request_id,
        request.method,
        request.url.path,
        request.url.query,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Internal server error. "
                f"request_id={request_id}. "
                "Check API logs for stack trace."
            )
        },
    )

if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)





