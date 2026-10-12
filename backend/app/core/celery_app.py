from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=f"redis://localhost:6379/0",
    backend=f"redis://localhost:6379/0"
)

celery_app.conf.task_routes = {
    "app.tasks.*": "main-queue",
}
