from fastapi import APIRouter
from app.api.endpoints import auth, businesses, clients, appointments, conversations, dashboard, webhooks

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
