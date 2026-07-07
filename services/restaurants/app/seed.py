"""Demo catalogue seeded at startup when ``Settings.seed_data`` is True (disabled in tests).

Stable, human-readable ids make the demo scripts and Swagger exploration easier.
"Chez Refus" has ``auto_accept=False`` on purpose: it demonstrates the SAGA
compensation path (kitchen ticket refused -> refund -> order cancelled).
"""

from app.repositories.entities import MenuItem, MenuItemOption, OpeningHour, Restaurant
from app.repositories.interfaces import MenuItemRepository, RestaurantRepository


def _all_week(open_time: str, close_time: str) -> list[OpeningHour]:
    return [OpeningHour(day=day, open=open_time, close=close_time) for day in range(7)]


def seed_catalogue(restaurants: RestaurantRepository, menu_items: MenuItemRepository) -> None:
    """Insert 3 realistic restaurants with their menus into the given repositories."""
    bella = Restaurant(
        id="resto-bella-napoli",
        name="La Bella Napoli",
        cuisine_type="italian",
        address="12 rue de la Roquette, 75011 Paris",
        lat=48.8555,
        lng=2.3730,
        opening_hours=_all_week("11:00", "23:00"),
        auto_accept=True,
    )
    sakura = Restaurant(
        id="resto-sakura-sushi",
        name="Sakura Sushi",
        cuisine_type="japanese",
        address="3 avenue de Choisy, 75013 Paris",
        lat=48.8210,
        lng=2.3652,
        opening_hours=_all_week("11:30", "22:00"),
        auto_accept=True,
    )
    refus = Restaurant(
        id="resto-chez-refus",
        name="Chez Refus",
        cuisine_type="french",
        address="27 boulevard Voltaire, 75011 Paris",
        lat=48.8600,
        lng=2.3700,
        # Closed on Sundays (day 6) — dinner service only.
        opening_hours=[OpeningHour(day=day, open="18:00", close="22:30") for day in range(6)],
        auto_accept=False,
    )
    for restaurant in (bella, sakura, refus):
        restaurants.add(restaurant)

    items = [
        MenuItem(
            id="dish-bella-margherita",
            restaurant_id=bella.id,
            name="Pizza Margherita",
            description="Tomate, mozzarella fior di latte, basilic frais",
            price=9.5,
            options=[
                MenuItemOption(name="Extra mozzarella", price_delta=1.5),
                MenuItemOption(name="Pate sans gluten", price_delta=2.0),
            ],
        ),
        MenuItem(
            id="dish-bella-regina",
            restaurant_id=bella.id,
            name="Pizza Regina",
            description="Tomate, mozzarella, jambon blanc, champignons",
            price=11.0,
            options=[MenuItemOption(name="Oeuf mollet", price_delta=1.0)],
        ),
        MenuItem(
            id="dish-bella-lasagne",
            restaurant_id=bella.id,
            name="Lasagne al forno",
            description="Lasagnes maison au boeuf et bechamel",
            price=12.5,
            options=[],
        ),
        MenuItem(
            id="dish-bella-calzone",
            restaurant_id=bella.id,
            name="Calzone",
            description="Pizza soufflee, ricotta, jambon, tomate",
            price=11.5,
            options=[MenuItemOption(name="Piment fort", price_delta=0.5)],
        ),
        MenuItem(
            id="dish-bella-tiramisu",
            restaurant_id=bella.id,
            name="Tiramisu",
            description="Mascarpone, cafe, cacao",
            price=6.0,
            options=[],
        ),
        MenuItem(
            id="dish-sakura-california",
            restaurant_id=sakura.id,
            name="California rolls saumon",
            description="8 pieces, avocat, concombre, sesame",
            price=8.9,
            options=[MenuItemOption(name="Gingembre extra", price_delta=0.5)],
        ),
        MenuItem(
            id="dish-sakura-sashimi",
            restaurant_id=sakura.id,
            name="Sashimi saumon",
            description="12 tranches de saumon frais",
            price=13.5,
            options=[],
        ),
        MenuItem(
            id="dish-sakura-ramen",
            restaurant_id=sakura.id,
            name="Ramen tonkotsu",
            description="Bouillon de porc, nouilles fraiches, oeuf marine",
            price=14.0,
            options=[
                MenuItemOption(name="Supplement chashu", price_delta=2.5),
                MenuItemOption(name="Nouilles extra", price_delta=1.5),
            ],
        ),
        MenuItem(
            id="dish-sakura-bento",
            restaurant_id=sakura.id,
            name="Bento du midi",
            description="Poulet teriyaki, riz, salade de chou, gyoza",
            price=15.9,
            options=[MenuItemOption(name="Miso soupe", price_delta=1.0)],
        ),
        MenuItem(
            id="dish-sakura-mochi",
            restaurant_id=sakura.id,
            name="Mochi glace",
            description="2 pieces, the matcha ou mangue",
            price=4.5,
            options=[],
        ),
        MenuItem(
            id="dish-refus-bourguignon",
            restaurant_id=refus.id,
            name="Boeuf bourguignon",
            description="Mijote au vin rouge, carottes, lardons",
            price=16.5,
            options=[MenuItemOption(name="Portion genereuse", price_delta=3.0)],
        ),
        MenuItem(
            id="dish-refus-canard",
            restaurant_id=refus.id,
            name="Confit de canard",
            description="Cuisse confite, pommes sarladaises",
            price=18.0,
            options=[],
        ),
        MenuItem(
            id="dish-refus-oignon",
            restaurant_id=refus.id,
            name="Soupe a l'oignon",
            description="Gratinee au comte",
            price=8.5,
            options=[MenuItemOption(name="Croutons extra", price_delta=0.5)],
        ),
        MenuItem(
            id="dish-refus-brulee",
            restaurant_id=refus.id,
            name="Creme brulee",
            description="A la vanille de Madagascar",
            price=7.0,
            options=[],
        ),
    ]
    for item in items:
        menu_items.add(item)
