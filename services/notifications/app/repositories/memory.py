"""In-memory implementations — stand-ins for a real database (ADR 0005).

Instances are created per application in ``create_app`` (stored on ``app.state``),
never as module-level globals, so every test starts from a clean state.
"""

from app.repositories.entities import Notification, RecipientType


class InMemoryNotificationRepository:
    """List-backed notification store (insertion order == chronological order)."""

    def __init__(self) -> None:
        self._notifications: list[Notification] = []

    def add(self, notification: Notification) -> None:
        self._notifications.append(notification)

    def list_filtered(
        self,
        recipient_type: RecipientType | None = None,
        recipient_id: str | None = None,
        event: str | None = None,
    ) -> list[Notification]:
        """Return matching notifications, most recent first."""
        matching = [
            notification
            for notification in self._notifications
            if (recipient_type is None or notification.recipient_type is recipient_type)
            and (recipient_id is None or notification.recipient_id == recipient_id)
            and (event is None or notification.event == event)
        ]
        return list(reversed(matching))
