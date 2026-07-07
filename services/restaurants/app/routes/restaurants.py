"""Restaurant profile endpoints: CRUD (hours included) and catalogue search."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies import MenuItemServiceDep, RestaurantServiceDep
from app.schemas.menu_items import MenuItemRead
from app.schemas.restaurants import (
    RestaurantCreate,
    RestaurantDetail,
    RestaurantRead,
    RestaurantUpdate,
)
from app.services.restaurant_service import DEFAULT_RADIUS_KM

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=list[RestaurantRead])
def search_restaurants(
    restaurant_service: RestaurantServiceDep,
    cuisine: Annotated[str | None, Query(max_length=50)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    lng: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    radius_km: Annotated[float, Query(gt=0.0, le=20000.0)] = DEFAULT_RADIUS_KM,
) -> list[RestaurantRead]:
    """Combinable filters: cuisine type, free text (restaurant or dish name), distance."""
    restaurants = restaurant_service.search(
        cuisine=cuisine, q=q, lat=lat, lng=lng, radius_km=radius_km
    )
    return [RestaurantRead.model_validate(restaurant) for restaurant in restaurants]


@router.post("", response_model=RestaurantRead, status_code=status.HTTP_201_CREATED)
def create_restaurant(
    payload: RestaurantCreate,
    restaurant_service: RestaurantServiceDep,
) -> RestaurantRead:
    restaurant = restaurant_service.create(payload)
    return RestaurantRead.model_validate(restaurant)


@router.get("/{restaurant_id}", response_model=RestaurantDetail)
def read_restaurant(
    restaurant_id: str,
    restaurant_service: RestaurantServiceDep,
    menu_item_service: MenuItemServiceDep,
) -> RestaurantDetail:
    """Full profile with the detailed menu."""
    restaurant = restaurant_service.get(restaurant_id)
    menu = menu_item_service.list_for_restaurant(restaurant_id)
    return RestaurantDetail(
        **RestaurantRead.model_validate(restaurant).model_dump(),
        menu=[MenuItemRead.model_validate(item) for item in menu],
    )


@router.put("/{restaurant_id}", response_model=RestaurantRead)
def update_restaurant(
    restaurant_id: str,
    payload: RestaurantUpdate,
    restaurant_service: RestaurantServiceDep,
) -> RestaurantRead:
    restaurant = restaurant_service.update(restaurant_id, payload)
    return RestaurantRead.model_validate(restaurant)
