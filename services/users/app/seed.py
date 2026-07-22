"""Default seed accounts loaded when ``USERS_SEED_DATA`` is True."""

from app.repositories.entities import User
from app.repositories.interfaces import UserRepository
from app.services.security import hash_password

SEED_USERS = [
    User(
        id="usr_alice",
        email="alice@example.com",
        password_hash=hash_password("Password123!"),
        name="Alice Martin (Client)",
        phone="+33612345678",
    ),
    User(
        id="usr_resto",
        email="chef@gourmet.fr",
        password_hash=hash_password("Password123!"),
        name="Le Chef (Restaurateur)",
        phone="+33698765432",
    ),
    User(
        id="usr_bob",
        email="bob@livreur.fr",
        password_hash=hash_password("Password123!"),
        name="Bob (Livreur Rapide)",
        phone="+33711223344",
    ),
]


def seed_users(user_repository: UserRepository) -> None:
    """Populate default accounts (client, restaurateur, livreur) if not present."""
    for user in SEED_USERS:
        if (
            user_repository.get_by_id(user.id) is None
            and user_repository.get_by_email(user.email) is None
        ):
            user_repository.add(user)
