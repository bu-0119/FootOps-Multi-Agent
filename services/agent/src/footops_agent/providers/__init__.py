"""External football-data provider adapters."""

from .base import DataProviderError, FootballDataProvider, ResourceNotFoundError
from .statsbomb_open import StatsBombOpenDataProvider

__all__ = [
    "DataProviderError",
    "FootballDataProvider",
    "ResourceNotFoundError",
    "StatsBombOpenDataProvider",
]
