"""FastAPI dependency wiring: repository (from app.state) -> services -> routes."""

from typing import Annotated

from fastapi import Depends, Request

from app.repositories.interfaces import NotificationRepository
from app.services.notification_service import NotificationService


def get_notification_repository(request: Request) -> NotificationRepository:
    repository: NotificationRepository = request.app.state.notification_repository
    return repository


def get_notification_service(
    notifications: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> NotificationService:
    return NotificationService(notifications)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
