import logging
import time
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Import all models to ensure they are registered with SQLModel metadata
# This must happen before any database operations to ensure relationships can be resolved
import ds_common.models  # noqa: F401
from ds_common.metrics.service import get_metrics_service


class PostgresManager:
    """
    PostgreSQL connection manager with support for read replicas.

    Provides async session management for database operations using SQLModel/SQLAlchemy.
    Supports separate read and write connections for load balancing.
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
        read_replica_url: str | None = None,
        read_replica_pool_size: int = 5,
        read_replica_max_overflow: int = 10,
    ):
        """
        Initialize PostgreSQL manager.

        Args:
            database_url: PostgreSQL connection URL for primary (write) database
            pool_size: Number of connections to maintain in the primary pool
            max_overflow: Maximum number of connections to allow beyond pool_size
            echo: Whether to log SQL queries (useful for debugging)
            read_replica_url: Optional PostgreSQL connection URL for read replica
            read_replica_pool_size: Number of connections to maintain in the read replica pool
            read_replica_max_overflow: Maximum overflow for read replica pool
        """
        self.database_url: str = database_url
        self.pool_size: int = pool_size
        self.max_overflow: int = max_overflow
        self.echo: bool = echo
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.metrics = get_metrics_service()

        # Primary (write) engine
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
            poolclass=NullPool if pool_size == 0 else None,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Read replica engine (optional)
        self.read_replica_enabled = read_replica_url is not None
        if read_replica_url:
            self.read_replica_engine = create_async_engine(
                read_replica_url,
                pool_size=read_replica_pool_size,
                max_overflow=read_replica_max_overflow,
                echo=echo,
                poolclass=NullPool if read_replica_pool_size == 0 else None,
            )
            self.read_replica_session_maker = async_sessionmaker(
                self.read_replica_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            self.logger.info("Read replica enabled")
        else:
            self.read_replica_engine = None
            self.read_replica_session_maker = None

        self.logger.debug("Initialized PostgreSQL manager...")

        # Set initial pool metrics
        self._update_pool_metrics()

    @classmethod
    async def create(
        cls,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
        read_replica_host: str | None = None,
        read_replica_port: int | None = None,
        read_replica_database: str | None = None,
        read_replica_user: str | None = None,
        read_replica_password: str | None = None,
        read_replica_pool_size: int = 5,
        read_replica_max_overflow: int = 10,
    ) -> "PostgresManager":
        """
        Create a new PostgreSQL manager instance.

        Args:
            host: PostgreSQL host for primary database
            port: PostgreSQL port for primary database
            database: Database name for primary database
            user: Database user for primary database
            password: Database password for primary database
            pool_size: Connection pool size for primary
            max_overflow: Maximum overflow connections for primary
            echo: Whether to echo SQL queries
            read_replica_host: Optional read replica host
            read_replica_port: Optional read replica port
            read_replica_database: Optional read replica database name
            read_replica_user: Optional read replica user
            read_replica_password: Optional read replica password
            read_replica_pool_size: Connection pool size for read replica
            read_replica_max_overflow: Maximum overflow for read replica

        Returns:
            PostgresManager instance
        """
        database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

        read_replica_url = None
        if read_replica_host:
            read_replica_port = read_replica_port or port
            read_replica_database = read_replica_database or database
            read_replica_user = read_replica_user or user
            read_replica_password = read_replica_password or password
            read_replica_url = (
                f"postgresql+asyncpg://{read_replica_user}:{read_replica_password}"
                f"@{read_replica_host}:{read_replica_port}/{read_replica_database}"
            )

        return cls(
            database_url=database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
            read_replica_url=read_replica_url,
            read_replica_pool_size=read_replica_pool_size,
            read_replica_max_overflow=read_replica_max_overflow,
        )

    @asynccontextmanager
    async def get_session(
        self,
        read_only: bool = False,
    ) -> AsyncGenerator[AsyncSession]:
        """
        Get an async database session.

        Args:
            read_only: If True and read replica is enabled, use read replica.
                      Otherwise, use primary (write) database.

        Yields:
            AsyncSession: SQLAlchemy async session

        Example:
            # Write session (default)
            async with postgres_manager.get_session() as session:
                player = Player(name="Test")
                session.add(player)

            # Read-only session (uses replica if enabled)
            async with postgres_manager.get_session(read_only=True) as session:
                result = await session.execute(select(Player))
                players = result.scalars().all()
        """
        # Use read replica if requested and available, otherwise use primary
        if read_only and self.read_replica_enabled and self.read_replica_session_maker:
            session_maker = self.read_replica_session_maker
        else:
            session_maker = self.async_session_maker

        operation = "read" if read_only else "write"
        start_time = time.time()
        status = "success"

        async with session_maker() as session:
            try:
                yield session
                # Only commit if not read-only (read-only sessions shouldn't modify data)
                if not read_only:
                    await session.commit()
            except Exception:
                await session.rollback()
                status = "error"
                self.logger.error(f"Error while using PostgreSQL session: {traceback.format_exc()}")
                raise
            finally:
                await session.close()
                duration = time.time() - start_time
                self.metrics.record_database_query(operation, duration, status)

    def _update_pool_metrics(self) -> None:
        """Update database pool metrics."""
        try:
            # Primary pool metrics
            pool = self.engine.pool
            if pool:
                pool_size = pool.size() if hasattr(pool, "size") else self.pool_size
                checked_in = pool.checkedin() if hasattr(pool, "checkedin") else 0
                checked_out = pool.checkedout() if hasattr(pool, "checkedout") else 0
                active = checked_out
                self.metrics.set_database_pool_metrics("primary", pool_size, active)

            # Read replica pool metrics
            if self.read_replica_engine:
                replica_pool = self.read_replica_engine.pool
                if replica_pool:
                    pool_size = (
                        replica_pool.size() if hasattr(replica_pool, "size") else self.pool_size
                    )
                    checked_out = (
                        replica_pool.checkedout() if hasattr(replica_pool, "checkedout") else 0
                    )
                    active = checked_out
                    self.metrics.set_database_pool_metrics("replica", pool_size, active)
        except Exception as e:
            self.logger.debug(f"Error updating pool metrics: {e}")

    async def close(self) -> None:
        """
        Close the database engine and all connections.
        """
        self.logger.debug("Closing PostgreSQL engines...")
        await self.engine.dispose()
        if self.read_replica_engine:
            await self.read_replica_engine.dispose()
