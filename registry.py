from scrapers.dealers.toyota.hollywood import ToyotaHollywoodScraper
from scrapers.dealers.toyota.north_hollywood import NorthHollywoodToyotaScraper
from scrapers.dealers.toyota.keyes import KeyesToyotaScraper
from scrapers.dealers.toyota.glendale import ToyotaGlendaleScraper
from scrapers.dealers.toyota.glendale import ToyotaGlendaleScraper
from scrapers.dealers.toyota.hamer import HamerToyotaScraper
from scrapers.dealers.toyota.nortridge import NorthridgeToyotaScraper

SCRAPERS = [
    ToyotaHollywoodScraper(),
    NorthHollywoodToyotaScraper(),
    KeyesToyotaScraper(),
    ToyotaGlendaleScraper(),
    HamerToyotaScraper(),
    NorthridgeToyotaScraper()
]
