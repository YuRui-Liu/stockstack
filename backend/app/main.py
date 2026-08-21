from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handling


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    upload_root = Path(resolved_settings.upload_root)
    upload_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    application = FastAPI(title="StockStack Product Management")
    application.state.settings = resolved_settings
    application.dependency_overrides[get_settings] = lambda: application.state.settings
    install_error_handling(application)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.mount(
        "/uploads",
        StaticFiles(directory=upload_root, check_dir=True),
        name="uploads",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
