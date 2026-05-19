from fastapi import FastAPI

from app.confirmations.router import router as confirmations_router
from app.core.config import Settings
from app.escalations.router import router as escalations_router
from app.feishu.router import router as feishu_router
from app.issues.router import router as issues_router
from app.projects.router import router as projects_router
from app.reviews.router import router as reviews_router
from app.tasks.router import router as tasks_router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title=active_settings.app_name)
    app.state.settings = active_settings
    app.include_router(projects_router)
    app.include_router(tasks_router)
    app.include_router(issues_router)
    app.include_router(feishu_router)
    app.include_router(confirmations_router)
    app.include_router(reviews_router)
    app.include_router(escalations_router)
    return app


app = create_app()
