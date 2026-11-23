"""Objects the handlers work with."""

from dataclasses import dataclass

from telegram.ext import Application, ContextTypes

from bot.scanner import FindListings, Scanner, find_listings
from car.car_model_catalog import CarModelCatalog
from storage.database import Database
from storage.listing_repository import ListingRepository
from storage.scan_repository import ScanRepository

_BOT_DATA_KEY = "services"


@dataclass(frozen=True)
class BotServices:
    """Everything the handlers need, shared by all chats."""

    database: Database
    scans: ScanRepository
    listings: ListingRepository
    scanner: Scanner
    model_catalog: CarModelCatalog

    @classmethod
    def create(cls, database_path: str, finder: FindListings = find_listings) -> "BotServices":
        """Create the services. The database still has to be opened.

        Args:
            database_path: Path of the database file
            finder: Blocking function that searches Yad2
        """
        database = Database(database_path)
        scans = ScanRepository(database)
        listings = ListingRepository(database)
        return cls(
            database=database,
            scans=scans,
            listings=listings,
            scanner=Scanner(scans, listings, finder),
            model_catalog=CarModelCatalog(),
        )


def set_services(app: Application, services: BotServices) -> None:
    """Make the services available to the app's handlers."""
    app.bot_data[_BOT_DATA_KEY] = services


def get_services(context: ContextTypes.DEFAULT_TYPE) -> BotServices:
    """Return the services of the app that runs the handler."""
    return context.bot_data[_BOT_DATA_KEY]
