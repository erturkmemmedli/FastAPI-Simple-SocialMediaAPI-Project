import logging
from contextlib import asynccontextmanager
from http.client import HTTPException

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler

from storeapi.database import database
from storeapi.routers.post import router as posts_router
from storeapi.routers.user import router as users_router
from storeapi.routers.upload import router as upload_router
from storeapi.logging_conf import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await database.connect()
    yield
    await database.disconnect()


app = FastAPI(lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
app.include_router(posts_router)
app.include_router(users_router)
app.include_router(upload_router)


@app.exception_handler(HTTPException)
async def http_exception_handler_logging(request, exc):
    logger.error(f"HTTPException: {exc.status_code} {exc.detail}")
    return http_exception_handler(request, exc)
