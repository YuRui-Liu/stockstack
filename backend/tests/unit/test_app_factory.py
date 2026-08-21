from app.core.config import Settings
from app.main import create_app


def test_create_app_owns_engine_for_resolved_database_url(tmp_path):
    database_url = "postgresql+asyncpg://custom.example:5432/custom"
    settings = Settings(
        database_url=database_url,
        jwt_secret="test-only-secret-with-enough-entropy",
        admin_password_hash="unused",
        upload_root=str(tmp_path / "uploads"),
    )

    application = create_app(settings)

    assert application.state.engine.url.render_as_string(hide_password=False) == database_url
    assert application.state.session_factory.kw["bind"] is application.state.engine
