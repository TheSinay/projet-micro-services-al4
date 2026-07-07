"""Read-side use cases over stored notifications."""

from app.repositories.entities import Notification, RecipientType
from app.repositories.interfaces import NotificationRepository


class NotificationService:
    """Query notifications for the demo and the frontend."""

    def __init__(self, notifications: NotificationRepository) -> None:
        self._notifications = notifications

    def list(
        self,
        recipient_type: RecipientType | None = None,
        recipient_id: str | None = None,
        event: str | None = None,
    ) -> list[Notification]:
        """Return matching notifications, most recent first."""
        return self._notifications.list_filtered(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            event=event,
        )
