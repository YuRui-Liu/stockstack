from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.core.errors import install_error_handling


def create_app() -> FastAPI:
    application = FastAPI(title="StockStack Product Management")
    install_error_handling(application)
    application.include_router(auth_router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
