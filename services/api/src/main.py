import logging
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from router import build_api_router
from database.connection import initialize_database
from core_logging import configure_logging
from seeds.keywords import ensure_default_keywords_seeded
from settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Card Reader API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_dev else settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(build_api_router())


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


@app.on_event("startup")
def on_startup() -> None:
    configure_logging()
    initialize_database()
    ensure_default_keywords_seeded()


