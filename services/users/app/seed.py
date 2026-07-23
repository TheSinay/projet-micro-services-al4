"""Default seed accounts loaded when ``USERS_SEED_DATA`` is True."""

from app.repositories.entities import Address, User
from app.repositories.interfaces import AddressRepository, UserRepository
from app.schemas.users import UserRole
from app.services.security import hash_password

SEED_USERS = [
    User(
        id="usr_alice",
        email="alice@example.com",
        password_hash=hash_password("Password123!"),
        name="Alice Martin (Client)",
        phone="+33612345678",
        role=UserRole.CLIENT,
    ),
    User(
        id="usr_resto",
        email="chef@gourmet.fr",
        password_hash=hash_password("Password123!"),
        name="Le Chef (Restaurateur)",
        phone="+33698765432",
        role=UserRole.RESTAURANT_OWNER,
    ),
    User(
        id="usr_bob",
        email="bob@livreur.fr",
        password_hash=hash_password("Password123!"),
        name="Bob (Livreur Rapide)",
        phone="+33711223344",
        role=UserRole.COURIER,
    ),
]


def seed_users(
    user_repository: UserRepository, address_repository: AddressRepository | None = None
) -> None:
    """Populate default accounts (client, restaurateur, livreur) and demo addresses if absent."""
    for user in SEED_USERS:
        if (
            user_repository.get_by_id(user.id) is None
            and user_repository.get_by_email(user.email) is None
        ):
            user_repository.add(user)

    if address_repository is not None and address_repository.get_by_id("addr_alice_home") is None:
        address_repository.add(
            Address(
                id="addr_alice_home",
                user_id="usr_alice",
                label="Domicile (Paris 11e)",
                street="15 rue de la Roquette",
                city="Paris",
                lat=48.8550,
                lng=2.3720,
            )
        )
