"""AccessMatrix local API application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles

from accessmatrix import __version__
from accessmatrix.api.routes.audit import (
    router as audit_router,
)
from accessmatrix.api.routes.authorization import (
    router as authorization_router,
)
from accessmatrix.api.routes.execution import (
    router as execution_router,
)
from accessmatrix.api.routes.findings import (
    router as findings_router,
)
from accessmatrix.api.routes.identities import (
    router as identities_router,
)
from accessmatrix.api.routes.projects import (
    router as projects_router,
)
from accessmatrix.api.routes.reports import (
    router as reports_router,
)
from accessmatrix.api.routes.scans import (
    router as scans_router,
)
from accessmatrix.api.routes.settings import (
    router as settings_router,
)
from accessmatrix.application.health import (
    build_health,
)
from accessmatrix.persistence.database import (
    initialize_database,
)

PACKAGE_DIRECTORY = Path(__file__).resolve().parent.parent

GUI_DIRECTORY = PACKAGE_DIRECTORY / "resources" / "gui"

GUI_INDEX = GUI_DIRECTORY / "index.html"

GUI_ASSETS = GUI_DIRECTORY / "assets"


def build_fallback_page() -> HTMLResponse:
    """Build a fallback page before the React GUI is compiled."""

    content = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >
        <title>AccessMatrix</title>
    </head>
    <body>
        <main>
            <h1>AccessMatrix</h1>
            <p>Backend operational.</p>
            <p>Version: {__version__}</p>
            <p>The React GUI has not been compiled.</p>
        </main>
    </body>
    </html>
    """

    return HTMLResponse(
        content=content,
    )


def create_app(
    *,
    initialize_storage: bool = True,
) -> FastAPI:
    """Create and configure the AccessMatrix API."""

    @asynccontextmanager
    async def lifespan(
        _: FastAPI,
    ) -> AsyncIterator[None]:
        if initialize_storage:
            initialize_database()

        yield

    application = FastAPI(
        title="AccessMatrix",
        description=("Local-first API authorization regression testing platform."),
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    application.include_router(projects_router)

    application.include_router(identities_router)

    application.include_router(authorization_router)

    application.include_router(execution_router)

    application.include_router(scans_router)

    application.include_router(findings_router)

    application.include_router(reports_router)

    application.include_router(settings_router)

    application.include_router(audit_router)

    @application.get(
        "/api/v1/health",
        tags=["System"],
        summary="Check application health",
    )
    def health() -> dict[str, str]:
        """Return the current application health."""

        return build_health()

    if GUI_ASSETS.is_dir():
        application.mount(
            "/assets",
            StaticFiles(
                directory=GUI_ASSETS,
            ),
            name="gui-assets",
        )

    @application.get(
        "/{full_path:path}",
        include_in_schema=False,
        response_model=None,
    )
    def frontend(
        full_path: str,
    ) -> Response:
        """Serve the React single-page application."""

        if full_path.startswith("api/"):
            raise HTTPException(
                status_code=404,
                detail="Not Found",
            )

        if not GUI_INDEX.is_file():
            return build_fallback_page()

        requested_path = (GUI_DIRECTORY / full_path).resolve()

        resolved_gui_directory = GUI_DIRECTORY.resolve()

        if (
            full_path
            and requested_path.is_relative_to(resolved_gui_directory)
            and requested_path.is_file()
        ):
            return FileResponse(requested_path)

        return FileResponse(GUI_INDEX)

    return application


app = create_app()
