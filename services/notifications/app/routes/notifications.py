"""Read endpoints over stored notifications (demo and frontend support)."""

from fastapi import APIRouter

from app.dependencies import NotificationServiceDep
from app.repositories.entities import RecipientType
from app.schemas.notifications import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    notification_service: NotificationServiceDep,
    recipient_type: RecipientType | None = None,
    recipient_id: str | None = None,
    event: str | None = None,
) -> list[NotificationRead]:
    notifications = notification_service.list(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        event=event,
    )
    return [NotificationRead.model_validate(notification) for notification in notifications]
