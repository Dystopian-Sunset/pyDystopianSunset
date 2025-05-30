import logging
import traceback
from contextlib import asynccontextmanager

from surrealdb import AsyncHttpSurrealConnection, AsyncSurreal, AsyncWsSurrealConnection


class SurrealManager:
    def __init__(self, url: str, namespace: str, database: str, username: str, password: str):
        self.url: str = url
        self.username: str = username
        self.password: str = password
        self.namespace: str = namespace
        self.database: str = database
        self.db: AsyncWsSurrealConnection | AsyncHttpSurrealConnection | None = None
        self.logger: logging.Logger = logging.getLogger(__name__)

        self.logger.debug("Initializing SurrealDB manager...")

    @classmethod
    async def create(cls, url: str, namespace: str, database: str, username: str, password: str) -> "SurrealManager":
        """
        Create a new SurrealDB manager instance
        """

        surreal_manager = cls(url, namespace, database, username, password)
        await surreal_manager._create_db_session()
        return surreal_manager
    
    @asynccontextmanager
    async def get_db(self) -> AsyncWsSurrealConnection | AsyncHttpSurrealConnection | None:
        if not self.db:
            self.db = await self._create_db_session()

        try:
            yield self.db
        except Exception:
            self.logger.error(f"Error while using SurrealDB connection: {traceback.format_exc()}")
            if self.db and isinstance(self.db, AsyncWsSurrealConnection):
                self.logger.debug("Closing SurrealDB Websocket connection...")
                await self.db.close()
                self.db = None
            raise

    async def _create_db_session(self) -> None:
        self.logger.debug("Creating SurrealDB connection...")

        try:
            db = AsyncSurreal(self.url)

            self.logger.debug("Signing in to SurrealDB...")
            await db.signin(
                {
                    "namespace": self.namespace,
                    "username": self.username,
                    "password": self.password,
                }
            )

            self.logger.debug("Using SurrealDB namespace: %s, database: %s", self.namespace, self.database)
            await db.use(self.namespace, self.database)

            self.db = db
        except Exception:
            self.logger.error(f"Failed to create SurrealDB connection: {traceback.format_exc()}")
            if db and isinstance(db, AsyncWsSurrealConnection):
                self.logger.debug("Closing SurrealDB Websocket connection...")
                await db.close()
            self.db = None
            raise