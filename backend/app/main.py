import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.core.config import Settings
from app.core.errors import install_error_handling


def create_app(settings: Settings | None = None) -> FastAPI:
    upload_root = (
        settings.upload_root
        if settings is not None
        else os.getenv("UPLOAD_ROOT", "/tmp/stockstack-uploads")
    )
    application = FastAPI(title="StockStack Product Management")
    install_error_handling(application)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.mount(
        "/uploads",
        StaticFiles(directory=upload_root, check_dir=False),
        name="uploads",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
