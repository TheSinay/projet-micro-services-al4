"""Demo seed data: three couriers at different Paris spots (one off-shift).

Enabled by ``Settings.seed_data`` (default True, disabled in tests) so the
assignment flow can be demonstrated right after startup.
"""

from app.repositories.entities import Courier, Location
from app.repositories.interfaces import CourierRepository


def _default_couriers() -> list[Courier]:
    return [
        Courier(
            id="usr_bob",
            name="Bob (Livreur Rapide)",
            phone="+33711223344",
            available=True,
            location=Location(lat=48.8566, lng=2.3522),  # Bastille / Paris
        ),
        Courier(
            id="courier-marco",
            name="Marco Rossi",
            phone="+33611111111",
            available=True,
            location=Location(lat=48.8867, lng=2.3431),  # Montmartre
        ),
        Courier(
            id="courier-lina",
            name="Lina Nguyen",
            phone="+33622222222",
            available=True,
            location=Location(lat=48.8462, lng=2.3372),  # Quartier latin
        ),
        Courier(
            id="courier-sofia",
            name="Sofia Almeida",
            phone="+33633333333",
            available=True,
            location=Location(lat=48.8708, lng=2.3033),  # Champs-Elysees
        ),
    ]


def seed_couriers(couriers: CourierRepository) -> None:
    """Insert the demo fleet into the repository."""
    for courier in _default_couriers():
        couriers.add(courier)
