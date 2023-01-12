import json
import sys
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium_stealth import stealth

CAPTCHA_TIMEOUT = 60
MIN_PRICE = 0
MAX_PRICE = 1500
N_PAGES = 100


class ANSI:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    NC = "\033[0m"


class WayfairOpenBox:
    base_url: str = f"https://www.wayfair.com/filters/furniture/sb1/sectionals-under-{MAX_PRICE}-c413893-p2490~{MIN_PRICE}~{MAX_PRICE}.html?itemsperpage=96&sortby=3"
    products_found: int = 0
    products: WebDriver
    scraper: WebDriver
    product_window: str
    scraper_window: str

    def __init__(self):
        print("Initializing...")
        self.scraper = self.build_selenium_stealth_driver()
        self.scraper_window = self.scraper.current_window_handle
        self.scraper.minimize_window()

    def build_selenium_stealth_driver(self, keep_open: bool = False) -> WebDriver:
        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        if keep_open:
            options.add_experimental_option("detach", True)

        # Requires chromedriver, present in PATH (brew install chromedriver --cask && chromedriver)
        driver = webdriver.Chrome(options=options)

        # Configure the driver for stealth mode
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        return driver

    def get_last_page_number(self) -> int:
        page = self.soupify(self.base_url)
        n_pages = page.find(
            "span", {"data-enzyme-id": "paginationLastPageLinkDisabled"}
        ).getText()
        return int(n_pages) if n_pages else N_PAGES

    def soupify(self, url: str) -> BeautifulSoup:
        i = 0
        self.scraper.get(url)
        while True:
            page = BeautifulSoup(self.scraper.page_source, "html.parser")
            if not page.select("form.Captcha"):
                break
            elif i >= CAPTCHA_TIMEOUT:
                quit()
            if not i:
                self.scraper.switch_to.window(self.scraper_window)
                self.scraper.set_window_rect(0, 0)
                print(
                    f"\nCaptcha triggered. Complete within {CAPTCHA_TIMEOUT} seconds to continue."
                )
            i += 1
            time.sleep(2)
        self.scraper.minimize_window()
        time.sleep(2)
        return page

    def scrape(self):
        n_pages = self.get_last_page_number()
        print(f"Scraping {n_pages} Wayfair product pages...")

        for i in range(1, n_pages + 1):
            print(".", end="")
            sys.stdout.flush()

            page = self.soupify(f"{self.base_url}&curpage={i}")
            for cooldown in range(0, 4):
                print(".", end="")
                sys.stdout.flush()
                time.sleep(1)

            for item in page.select("a:has(span[type=OPEN_BOX])"):
                print(f"{ANSI.GREEN}x{ANSI.NC}", end="")
                sys.stdout.flush()
                if not self.products_found:
                    # Create a second driver for the open box items
                    self.products = self.build_selenium_stealth_driver(keep_open=True)
                    self.product_window = self.products.current_window_handle
                    self.products.minimize_window()
                else:
                    # Open product in new tab
                    self.products.execute_script("window.open('');")
                    self.products.switch_to.window(
                        self.products.window_handles[self.products_found]
                    )
                self.products_found += 1
                self.products.get(f'{item["href"]}&clearance=true')

        self.scraper.close()

        if self.products_found:
            self.products.switch_to.window(self.product_window)
            self.products.set_window_rect(0, 0)

        print(f"\n\nFound {self.products_found} open box products.")


WayfairOpenBox().scrape()
