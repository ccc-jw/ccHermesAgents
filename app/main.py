from fastapi import FastAPI

from app.core.config import Settings
from app.projects.router import router as projects_router
from app.tasks.router import router as tasks_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title=active_settings.app_name)
    app.state.settings = active_settings
    app.include_router(projects_router)
    app.include_router(tasks_router)
    return app


app = create_app()
