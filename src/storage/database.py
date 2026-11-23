"""SQLite connection, transactions and schema migrations."""

import asyncio
import contextlib
from collections.abc import AsyncIterator, Iterator, Sequence
from pathlib import Path

import aiosqlite

from common.exceptions import CustomException, ErrorCode
from common.logger import logger
from storage.migrations import MIGRATIONS


class Database:
    """The bot's SQLite database."""

    def __init__(self, path: str) -> None:
        """Initialize a Database. It is opened with `open`.

        Args:
            path: Path of the database file, created with its folder if missing
        """
        self._path = Path(path)
        self._connection: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def open(self) -> None:
        """Connect and bring the schema up to date.

        Raises:
            CustomException: If the database cannot be opened or migrated
        """
        try:
            await self._connect()
            await self._migrate()
        except BaseException:
            # The connection's thread would keep the process from exiting.
            await self.close()
            raise

    async def close(self) -> None:
        """Close the connection, if it is open."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def fetch_all(self, query: str, parameters: Sequence = ()) -> list[aiosqlite.Row]:
        """Return every row of a query.

        Raises:
            CustomException: If the query fails
        """
        with _translate_errors("read"):
            return list(await self._connected.execute_fetchall(query, parameters))

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Run statements that are committed together, or not at all.

        Usage:
            async with database.transaction() as connection:
                await connection.execute(...)

        Raises:
            CustomException: If a statement fails
        """
        async with self._write_lock:
            with _translate_errors("write"):
                await self._connected.execute("BEGIN IMMEDIATE")
                try:
                    yield self._connected
                except BaseException:
                    await self._connected.execute("ROLLBACK")
                    raise
                await self._connected.execute("COMMIT")

    @property
    def _connected(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise CustomException(
                message="The database is not open", error_code=ErrorCode.STORAGE_FAILED
            )
        return self._connection

    async def _connect(self) -> None:
        with _translate_errors(f"open {self._path}"):
            await asyncio.to_thread(self._path.parent.mkdir, parents=True, exist_ok=True)
            # Transactions are started explicitly, see `transaction`.
            self._connection = await aiosqlite.connect(self._path, isolation_level=None)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.execute("PRAGMA journal_mode = WAL")

    async def _migrate(self) -> None:
        applied = (await self.fetch_all("PRAGMA user_version"))[0][0]
        for version, statements in enumerate(MIGRATIONS[applied:], start=applied + 1):
            async with self.transaction() as connection:
                for statement in statements:
                    await connection.execute(statement)
                await connection.execute(f"PRAGMA user_version = {version}")
            logger.info("Database migrated", version=version)


@contextlib.contextmanager
def _translate_errors(action: str) -> Iterator[None]:
    """Raise database errors as CustomException."""
    try:
        yield
    except (aiosqlite.Error, OSError) as err:
        logger.error("Database failed", action=action, error=str(err))
        raise CustomException(
            message=f"Database failed to {action}: {err}",
            error_code=ErrorCode.STORAGE_FAILED,
        ) from err
