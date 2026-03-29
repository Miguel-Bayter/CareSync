"""Generic base repository providing common CRUD operations."""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository with basic persistence operations.

    Sub-classes must provide the model class via the ``model_class`` attribute.

    Args:
        db: An active SQLAlchemy Session.
    """

    model_class: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_by_id(self, id: UUID) -> ModelT | None:
        """Return the entity with the given primary key, or None if not found.

        Args:
            id: UUID primary key of the entity.

        Returns:
            The entity instance, or None.
        """
        return self.db.get(self.model_class, id)

    def save(self, entity: ModelT) -> ModelT:
        """Persist a new or modified entity within the current transaction.

        Flushes to the database so that auto-generated values (e.g. server
        defaults) are populated, but does NOT commit — the caller (service
        layer) owns the transaction boundary.

        Args:
            entity: The ORM model instance to persist.

        Returns:
            The flushed entity (same object, with server-side values filled in).
        """
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        """Remove an entity from the database within the current transaction.

        Args:
            entity: The ORM model instance to delete.
        """
        self.db.delete(entity)
        self.db.flush()
