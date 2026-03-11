from fastapi import APIRouter

from app.api.actions import router as actions_router
from app.api.meetings import router as meetings_router

api_router = APIRouter()
api_router.include_router(meetings_router)
api_router.include_router(actions_router)
