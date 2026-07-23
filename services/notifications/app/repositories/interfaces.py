"""Abstract repository interfaces (structural typing via Protocol).

Business logic depends only on these contracts, so the in-memory implementation
can later be swapped for a real database without touching the services.
"""

from typing import Protocol

from app.repositories.entities import Notification, RecipientType


class NotificationRepository(Protocol):
    """Persistence contract for notifications."""

    def add(self, notification: Notification) -> None: ...

    def list_filtered(
        self,
        recipient_type: RecipientType | None = None,
        recipient_id: str | None = None,
        event: str | None = None,
    ) -> list[Notification]: ...
