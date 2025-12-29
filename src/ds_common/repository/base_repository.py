import logging
from collections.abc import Awaitable, Callable
from datetime import UTC
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ds_common.models.base_model import BaseSQLModel
from ds_discord_bot.postgres_manager import PostgresManager

T = TypeVar("T", bound=BaseSQLModel)
R = TypeVar("R")


class BaseRepository[T]:
    """
    Base repository class using SQLModel/SQLAlchemy ORM.

    Provides common CRUD operations for all models.
    """

    def __init__(
        self,
        postgres_manager: PostgresManager,
        model_class: type[T],
    ):
        """
        Initialize the repository.

        Args:
            postgres_manager: PostgreSQL manager for database sessions
            model_class: The SQLModel class this repository manages
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.postgres_manager: PostgresManager = postgres_manager
        self.model_class: type[T] = model_class

    async def _with_session(
        self,
        func: Callable[[AsyncSession], Awaitable[R]],
        session: AsyncSession | None = None,
        read_only: bool = False,
    ) -> R:
        """
        Execute a function with either the provided session or a new one.

        This utility method handles the common pattern of:
        - If session is provided, use it directly
        - If session is None, create a new session from postgres_manager
        - If read_only is True, use read replica if available

        Args:
            func: Async function that takes an AsyncSession and returns a result
            session: Optional database session to use
            read_only: If True and session is None, use read replica for read operations

        Returns:
            Result from the function execution
        """
        if session:
            return await func(session)
        async with self.postgres_manager.get_session(read_only=read_only) as sess:
            return await func(sess)

    async def get_by_field(
        self,
        field: str,
        value: Any,
        case_sensitive: bool = True,
        session: AsyncSession | None = None,
        read_only: bool = True,
    ) -> T | None:
        """
        Get a model by a field value.

        Args:
            field: Field name to search by
            value: Value to search for
            case_sensitive: Whether the search should be case sensitive
            session: Optional database session (uses manager's session if not provided)
            read_only: If True and session is None, use read replica for read operations

        Returns:
            Model instance or None if not found
        """
        if field not in self.model_class.model_fields:
            raise ValueError(f"Field {field} not found in model {self.model_class}")

        field_attr = getattr(self.model_class, field)

        if case_sensitive:
            stmt = select(self.model_class).where(field_attr == value)
        else:
            # For case-insensitive search, use ILIKE for strings
            if isinstance(value, str):
                from sqlalchemy import func

                stmt = select(self.model_class).where(func.lower(field_attr) == func.lower(value))
            else:
                stmt = select(self.model_class).where(field_attr == value)

        self.logger.debug(f"Query: {stmt}")

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return result.scalar_one_or_none()

        result = await self._with_session(_execute, session, read_only=read_only)
        self.logger.debug(f"Result: {result}")
        return result

    async def get_by_id(
        self, id: UUID | str, session: AsyncSession | None = None, read_only: bool = True
    ) -> T | None:
        """
        Get a model by ID.

        Args:
            id: UUID or string UUID
            session: Optional database session
            read_only: If True and session is None, use read replica for read operations

        Returns:
            Model instance or None if not found
        """
        if isinstance(id, str):
            id = UUID(id)

        self.logger.debug(f"Getting {self.model_class.__name__} by id: {id}")

        async def _execute(sess: AsyncSession):
            return await sess.get(self.model_class, id)

        result = await self._with_session(_execute, session, read_only=read_only)
        self.logger.debug(f"Result: {result}")
        return result

    async def get_all(self, session: AsyncSession | None = None, read_only: bool = True) -> list[T]:
        """
        Get all models.

        Args:
            session: Optional database session
            read_only: If True and session is None, use read replica for read operations

        Returns:
            List of model instances
        """
        self.logger.debug(f"Getting all {self.model_class.__name__}")

        stmt = select(self.model_class)

        async def _execute(sess: AsyncSession):
            result = await sess.execute(stmt)
            return list(result.scalars().all())

        result = await self._with_session(_execute, session, read_only=read_only)
        self.logger.debug(f"Result: {len(result)} records found")
        return result

    async def create(self, model: T, session: AsyncSession | None = None) -> T:
        """
        Create a new model.

        Args:
            model: Model instance to create
            session: Optional database session

        Returns:
            Created model instance
        """

        async def _execute(sess: AsyncSession):
            sess.add(model)
            await sess.commit()
            await sess.refresh(model)
            return model

        result = await self._with_session(_execute, session)
        self.logger.debug(f"Created {self.model_class.__name__} {result.id}")
        return result

    async def update(self, model: T, session: AsyncSession | None = None) -> T:
        """
        Update an existing model.

        Args:
            model: Model instance to update
            session: Optional database session

        Returns:
            Updated model instance
        """

        async def _execute(sess: AsyncSession):
            # Update updated_at timestamp
            from datetime import datetime

            model.updated_at = datetime.now(UTC)

            sess.add(model)
            await sess.commit()
            await sess.refresh(model)
            return model

        result = await self._with_session(_execute, session)
        self.logger.debug(f"Updated {self.model_class.__name__} {result.id}")
        return result

    async def upsert(self, model: T, session: AsyncSession | None = None) -> T:
        """
        Insert or update a model (upsert).

        Args:
            model: Model instance to upsert
            session: Optional database session

        Returns:
            Upserted model instance
        """
        if model.id:
            existing = await self.get_by_id(model.id, session=session)
            if existing:
                # Update existing
                for key, value in model.model_dump(exclude={"id", "created_at"}).items():
                    setattr(existing, key, value)
                return await self.update(existing, session=session)

        # Create new
        return await self.create(model, session=session)

    async def delete(self, id: UUID | str, session: AsyncSession | None = None) -> None:
        """
        Delete a model by ID.

        Args:
            id: UUID or string UUID
            session: Optional database session
        """
        if isinstance(id, str):
            id = UUID(id)

        async def _execute(sess: AsyncSession):
            model = await sess.get(self.model_class, id)
            if model:
                await sess.delete(model)
                await sess.commit()
                self.logger.debug(f"Deleted {self.model_class.__name__} {id}")
            else:
                self.logger.warning(f"{self.model_class.__name__} {id} not found for deletion")

        await self._with_session(_execute, session)
