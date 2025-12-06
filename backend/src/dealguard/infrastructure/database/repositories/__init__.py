"""Repository pattern implementations for database access."""

from dealguard.infrastructure.database.repositories.base import BaseRepository
from dealguard.infrastructure.database.repositories.contract import ContractRepository

__all__ = [
    "BaseRepository",
    "ContractRepository",
]
