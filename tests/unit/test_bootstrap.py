from app.main import create_app
from app.core.config import Settings


def test_create_app_has_title():
    app = create_app()
    assert app.title == "Hermes Agent"


def test_default_settings_use_local_storage():
    settings = Settings()
    assert settings.storage_root == "./storage"
    assert settings.database_url == "sqlite:///./hermes.db"
