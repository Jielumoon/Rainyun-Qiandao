"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from rainyun.web.errors import ApiError
from rainyun.web.responses import error_response
from rainyun.web.routes import (
    accounts_router,
    actions_router,
    auth_router,
    servers_router,
    system_router,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Rainyun Web API")

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=error_response(exc.message, code=1)
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(status_code=500, content=error_response("系统异常", code=1))

    app.include_router(accounts_router)
    app.include_router(auth_router)
    app.include_router(servers_router)
    app.include_router(system_router)
    app.include_router(actions_router)

    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon() -> Response:
            return Response(status_code=204)

    return app


app = create_app()
