from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HERMES_", env_file=".env", extra="ignore")

    app_name: str = "Hermes Agent"
    database_url: str = "sqlite:///./hermes.db"
    storage_root: str = "./storage"
    runner_timeout_seconds: int = 1800
    runner_max_output_bytes: int = 5_000_000
    runner_api_base_url: str = ""
    runner_api_key_env: str = "HERMES_RUNNER_API_KEY"
    runner_model: str = ""
