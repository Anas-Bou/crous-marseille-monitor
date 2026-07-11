import os

from dotenv import load_dotenv

load_dotenv()


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Exact Marseille search requested for the active CROUS campaign.
MARSEILLE_SEARCH_URL = os.getenv(
    "CROUS_SEARCH_URL",
    "https://trouverunlogement.lescrous.fr/tools/47/search?"
    "bounds=5.2286902_43.3910329_5.5324758_43.1696205&"
    "locationName=Marseille+%2813000%29",
)

CHECK_INTERVAL_SECONDS = env_int("CHECK_INTERVAL_SECONDS", 120)
HEADLESS = env_bool("HEADLESS", True)
DISABLE_SOUND = env_bool("DISABLE_SOUND", False)
BROWSER_BINARY = os.getenv("CHROME_BINARY") or os.getenv("BROWSER_BINARY")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
AVAILABLE_RESIDENCES_FILE = os.getenv(
    "AVAILABLE_RESIDENCES_FILE",
    os.getenv("SEEN_RESIDENCES_FILE", "available_residences_marseille.txt"),
)
DAILY_SUMMARY_FILE = os.getenv(
    "DAILY_SUMMARY_FILE", "daily_summary_marseille.json"
)
SUMMARY_TIMEZONE = os.getenv("SUMMARY_TIMEZONE", "Europe/Paris")
