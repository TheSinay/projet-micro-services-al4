"""Kitchen ticket endpoints: creation (accept/refuse) and preparation lifecycle."""

from fastapi import APIRouter, status

from app.dependencies import KitchenTicketServiceDep
from app.repositories.entities import TicketStatus
from app.schemas.tickets import KitchenTicketCreate, KitchenTicketRead, KitchenTicketStatusUpdate

router = APIRouter(tags=["kitchen-tickets"])


@router.get(
    "/restaurants/{restaurant_id}/kitchen-tickets",
    response_model=list[KitchenTicketRead],
)
def list_kitchen_tickets(
    restaurant_id: str,
    ticket_service: KitchenTicketServiceDep,
    status: TicketStatus | None = None,
) -> list[KitchenTicketRead]:
    """List a restaurant's kitchen tickets (insertion order).

    Optionally filter by ``status`` (ACCEPTED/REFUSED/PREPARING/READY) via the
    ``?status=`` query parameter. Returns 200 with ``[]`` when the kitchen is
    empty, and 404 when the restaurant is unknown.
    """
    tickets = ticket_service.list_by_restaurant(restaurant_id, status)
    return [KitchenTicketRead.model_validate(ticket) for ticket in tickets]


@router.post(
    "/restaurants/{restaurant_id}/kitchen-tickets",
    response_model=KitchenTicketRead,
    status_code=status.HTTP_201_CREATED,
)
def create_kitchen_ticket(
    restaurant_id: str,
    payload: KitchenTicketCreate,
    ticket_service: KitchenTicketServiceDep,
) -> KitchenTicketRead:
    """201 ACCEPTED when ``auto_accept`` is on; 409 when the restaurant refuses."""
    ticket = ticket_service.create(restaurant_id, payload)
    return KitchenTicketRead.model_validate(ticket)


@router.patch("/kitchen-tickets/{ticket_id}", response_model=KitchenTicketRead)
async def update_kitchen_ticket_status(
    ticket_id: str,
    payload: KitchenTicketStatusUpdate,
    ticket_service: KitchenTicketServiceDep,
) -> KitchenTicketRead:
    """Strict transitions ACCEPTED -> PREPARING -> READY; READY publishes ``order.ready``."""
    ticket = await ticket_service.update_status(ticket_id, payload.status)
    return KitchenTicketRead.model_validate(ticket)
