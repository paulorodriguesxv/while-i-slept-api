"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from while_i_slept_api.api.errors import register_exception_handlers
from while_i_slept_api.api.routers.auth import router as auth_router
from while_i_slept_api.api.routers.briefings import router as briefings_router
from while_i_slept_api.api.routers.feed import router as feed_router
from while_i_slept_api.api.routers.me import router as me_router
from while_i_slept_api.api.routers.webhooks import router as webhooks_router

origins = ["*"]  # allow all origins for now


def create_app() -> FastAPI:
    """Create the FastAPI application with only the MVP endpoints enabled."""

    app = FastAPI(
        title="What Happened While I Slept API",
        version="0.1.0",
        #docs_url=None, # disable docs when in production, but enable in development
        #redoc_url=None,
        #openapi_url=None,
    )
    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(briefings_router)
    app.include_router(feed_router)
    app.include_router(webhooks_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )    
    return app


app = create_app()
