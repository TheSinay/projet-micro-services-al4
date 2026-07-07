"""User registration and profile endpoints."""

from fastapi import APIRouter, status

from app.dependencies import CurrentUser, UserServiceDep
from app.schemas.users import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, user_service: UserServiceDep) -> UserRead:
    user = user_service.register(payload)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def read_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
def update_profile(
    payload: UserUpdate,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> UserRead:
    user = user_service.update_profile(current_user, payload)
    return UserRead.model_validate(user)
