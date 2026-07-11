import argparse
import hashlib
import html
import logging
import os
import subprocess
import time
from dataclasses import dataclass

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import (
    AVAILABLE_RESIDENCES_FILE,
    BROWSER_BINARY,
    CHECK_INTERVAL_SECONDS,
    DISABLE_SOUND,
    HEADLESS,
    MARSEILLE_SEARCH_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MAX_TELEGRAM_MESSAGE_LENGTH = 3500


@dataclass(frozen=True)
class Listing:
    residence_id: str
    title: str
    address: str
    price: str
    url: str

    def telegram_text(self):
        details = [f"<b>{html.escape(self.title)}</b>", html.escape(self.address)]
        if self.price:
            details.append(html.escape(self.price))
        if self.url:
            details.append(
                f"<a href='{html.escape(self.url, quote=True)}'>Ouvrir le logement</a>"
            )
        return "\n".join(details)


class CrousMonitor:
    def __init__(
        self,
        search_url=MARSEILLE_SEARCH_URL,
        interval_seconds=CHECK_INTERVAL_SECONDS,
        available_residences_file=AVAILABLE_RESIDENCES_FILE,
        browser_binary=BROWSER_BINARY,
        headless=HEADLESS,
        disable_sound=DISABLE_SOUND,
    ):
        self.search_url = search_url
        self.latest_results_url = search_url
        self.interval_seconds = interval_seconds
        self.available_residences_file = available_residences_file
        self.browser_binary = browser_binary
        self.headless = headless
        self.disable_sound = disable_sound
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.previous_available_ids = self.load_available_residences()

    def load_available_residences(self):
        residence_ids = set()
        try:
            if os.path.exists(self.available_residences_file):
                with open(
                    self.available_residences_file, "r", encoding="utf-8"
                ) as file:
                    residence_ids = {line.strip() for line in file if line.strip()}
        except OSError as exc:
            logging.warning("Could not load availability state: %s", exc)

        logging.info("Loaded %s previously available listings", len(residence_ids))
        return residence_ids

    def save_available_residences(self, residence_ids):
        with open(self.available_residences_file, "w", encoding="utf-8") as file:
            for residence_id in sorted(residence_ids):
                file.write(f"{residence_id}\n")

    def setup_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if self.browser_binary:
            options.binary_location = self.browser_binary
            logging.info("Using browser binary: %s", self.browser_binary)

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        logging.info("Browser started successfully")
        return driver

    def send_telegram_message(self, message):
        response = requests.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            data={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )

        if response.status_code == 200:
            logging.info("Telegram notification sent successfully")
            return True

        logging.error(
            "Telegram error %s: %s", response.status_code, response.text
        )
        return False

    def send_telegram_messages(self, messages):
        try:
            return all(self.send_telegram_message(message) for message in messages)
        except requests.RequestException as exc:
            logging.error("Could not contact Telegram: %s", exc)
            return False

    def play_sound_notification(self):
        if self.disable_sound:
            return

        for command in (
            ["speaker-test", "-t", "sine", "-f", "1000", "-l", "1"],
            ["spd-say", "New CROUS accommodation found in Marseille"],
        ):
            try:
                subprocess.run(
                    command,
                    timeout=5,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                return
            except (OSError, subprocess.TimeoutExpired):
                continue

    @staticmethod
    def first_element_text(card, selectors):
        for selector in selectors:
            elements = card.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                text = element.text.strip()
                if text:
                    return text
        return ""

    def parse_listing(self, card):
        card_text = card.text.strip()
        lines = [line.strip() for line in card_text.splitlines() if line.strip()]
        address = next(
            (line for line in lines if "marseille" in line.casefold()), ""
        )

        # This explicit check prevents nearby Aix-en-Provence or Aubagne results
        # from ever being included in a Telegram notification.
        if not address:
            return None

        title = self.first_element_text(
            card, ["h3", "h2", ".fr-card__title", "[class*='title']"]
        )
        if not title:
            address_index = lines.index(address)
            candidates = [
                line
                for line in lines[:address_index]
                if "EUR" not in line.upper() and "€" not in line
            ]
            title = candidates[-1] if candidates else "Logement CROUS Marseille"

        price = next((line for line in lines if "€" in line), "")
        links = card.find_elements(By.CSS_SELECTOR, "a[href]")
        listing_url = links[0].get_attribute("href") if links else ""
        stable_value = listing_url or f"{title}|{address}|{price}"
        residence_id = hashlib.sha256(stable_value.encode("utf-8")).hexdigest()

        return Listing(residence_id, title, address, price, listing_url)

    def search_accommodations(self, driver):
        logging.info("Searching only CROUS accommodations in Marseille")
        driver.get(self.search_url)
        wait = WebDriverWait(driver, 25)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.latest_results_url = driver.current_url
        logging.info("CROUS results URL: %s", self.latest_results_url)
        time.sleep(3)

        cards = []
        for selector in (
            ".fr-card",
            "article",
            ".tl-card",
            ".card",
            "[class*='card']",
        ):
            candidates = driver.find_elements(By.CSS_SELECTOR, selector)
            marseille_cards = [
                card
                for card in candidates
                if "marseille" in card.text.casefold()
            ]
            if marseille_cards:
                cards = marseille_cards
                logging.info(
                    "Found %s Marseille cards with selector %s",
                    len(cards),
                    selector,
                )
                break

        if not cards:
            body_text = driver.find_element(By.TAG_NAME, "body").text.casefold()
            if "0 logement" in body_text or "aucun logement trouvé" in body_text:
                logging.info("The CROUS page currently reports zero Marseille listings")
                return {}
            logging.error("Unexpected CROUS page content: %s", body_text[:1500])
            raise RuntimeError(
                "No Marseille listing cards were detected; the CROUS page may have changed"
            )

        listings = {}
        for card in cards:
            try:
                listing = self.parse_listing(card)
                if listing:
                    listings[listing.residence_id] = listing
            except Exception as exc:
                logging.debug("Could not parse a listing card: %s", exc)

        if not listings:
            raise RuntimeError("Marseille cards were found but none could be parsed")

        logging.info("Detected %s currently available Marseille listings", len(listings))
        return listings

    def build_notifications(self, new_listings):
        header = "<b>NOUVEAUX LOGEMENTS CROUS DISPONIBLES A MARSEILLE</b>"
        footer = (
            f"\n\n<a href='{html.escape(self.latest_results_url, quote=True)}'>"
            "Voir tous les logements CROUS Marseille</a>"
        )
        notifications = []
        current_message = header

        for listing in new_listings:
            block = f"\n\n{listing.telegram_text()}"
            if len(current_message) + len(block) + len(footer) > MAX_TELEGRAM_MESSAGE_LENGTH:
                notifications.append(current_message + footer)
                current_message = header + block
            else:
                current_message += block

        notifications.append(current_message + footer)
        return notifications

    def run_check(self, driver):
        current_listings = self.search_accommodations(driver)
        current_ids = set(current_listings)
        new_listings = [
            listing
            for residence_id, listing in current_listings.items()
            if residence_id not in self.previous_available_ids
        ]

        if new_listings:
            logging.info("Found %s newly available Marseille listings", len(new_listings))
            if not self.send_telegram_messages(self.build_notifications(new_listings)):
                logging.warning("Availability state was not changed; notification will retry")
                return False
            self.play_sound_notification()
        else:
            logging.info("No new Marseille listings")

        # Store only what is currently available. A listing that disappears and
        # later returns will therefore trigger a new Telegram notification.
        self.save_available_residences(current_ids)
        self.previous_available_ids = current_ids
        return True

    def monitor(self, once=False):
        while True:
            check_succeeded = False
            last_error = None

            for attempt in range(1, 3):
                driver = None
                try:
                    driver = self.setup_driver()
                    self.run_check(driver)
                    check_succeeded = True
                    break
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    last_error = exc
                    logging.exception(
                        "CROUS Marseille check failed (attempt %s/2)", attempt
                    )
                    if attempt == 1:
                        logging.info("Restarting Chrome automatically in 10 seconds")
                        time.sleep(10)
                finally:
                    if driver is not None:
                        try:
                            driver.quit()
                        except Exception:
                            logging.debug("Chrome was already disconnected")

            if once:
                if not check_succeeded and last_error is not None:
                    raise last_error
                break

            logging.info("Waiting %s seconds", self.interval_seconds)
            time.sleep(self.interval_seconds)

    def preview_once(self):
        driver = self.setup_driver()
        try:
            listings = self.search_accommodations(driver)
            logging.info("Dry run: %s Marseille listings detected", len(listings))
            for listing in listings.values():
                logging.info("%s | %s | %s", listing.title, listing.address, listing.price)
        finally:
            driver.quit()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Monitor only CROUS accommodations in Marseille."
    )
    parser.add_argument("--once", action="store_true", help="Run one check and exit.")
    parser.add_argument(
        "--interval", type=int, default=CHECK_INTERVAL_SECONDS
    )
    parser.add_argument("--browser-binary", default=BROWSER_BINARY)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--no-sound", action="store_true", default=DISABLE_SOUND)
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="Send a Telegram test message without opening CROUS.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect Marseille listings without Telegram or state changes.",
    )
    return parser.parse_args()


def main(force_disable_sound=False):
    args = parse_args()
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise SystemExit(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env or GitHub secrets."
        )

    monitor = CrousMonitor(
        interval_seconds=args.interval,
        browser_binary=args.browser_binary,
        headless=not args.no_headless and HEADLESS,
        disable_sound=args.no_sound or force_disable_sound,
    )

    if args.test_telegram:
        if not monitor.send_telegram_message(
            "Bot CROUS Marseille operationnel. Les alertes Telegram sont configurees."
        ):
            raise SystemExit(1)
        return

    if args.dry_run:
        monitor.preview_once()
        return

    monitor.monitor(once=args.once)


if __name__ == "__main__":
    main()
