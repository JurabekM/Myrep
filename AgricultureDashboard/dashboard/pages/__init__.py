"""Page registry — importing this package registers every @ui.page route."""
from dashboard.pages import (  # noqa: F401 - imports register the routes
    admin_page,
    ai_page,
    analytics_page,
    finance_page,
    home,
    irrigation_page,
    login,
    map_page,
    market_page,
    ml_page,
    reports_page,
    satellite_page,
    settings_page,
    weather_page,
)
