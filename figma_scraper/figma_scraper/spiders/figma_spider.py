import math
import random
import time
import logging
import scrapy
from scrapy.selector import Selector
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime


param_map = {
    'recent': 'new',  # https://www.figma.com/community/files/figma/free/new
    'trending': '',  # https://www.figma.com/community/files/figma/free/
    'popular': 'popular'  # https://www.figma.com/community/files/figma/free/popular
}


class FigmaSpider(scrapy.Spider):
    name = 'figma_spider'
    start_urls = []
    target = 'recent'
    has_cancel = False
    cancelation_tokens_count = 30
    cancelation_tokens = set()
    next_cancelation_tokens = None

    def __init__(self, target='popular', cancelation_tokens=None, randomize=False, **kwargs):
        # setup logging
        now = datetime.now()
        iso_now = now.replace(microsecond=0).isoformat()
        logfile = f"figma-spider-{iso_now}.log"
        logging.basicConfig(
            filename=logfile,
            filemode="a",
            level=logging.WARN,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

        # recent, trending, popular , e.g. pass with -a target=recent
        self.target = target

        # read the cancelation tokens file if provided
        if cancelation_tokens:
            self.cancelation_tokens = set(cancelation_tokens)
            self.has_cancel = True
            self.cancelation_tokens_count = len(cancelation_tokens)
            self.next_cancelation_tokens = set()

            logging.info(
                f"{self.cancelation_tokens_count} cancelation tokens received")

        # randomize for long-running job, to avoid bot-detection (if there is one)
        self.randomize = randomize

        self.start_urls = [
            f'https://www.figma.com/community/files/figma/free/{param_map[target]}']
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(service=Service(
            executable_path=ChromeDriverManager().install()), options=options)

    scraped_data = []
    scraped_ids = set()

    def push(self, id, data):
        self.scraped_data.append(data)
        self.scraped_ids.add(id)

        # update next cancelation tokens
        # the first item is the newest, which should be used as the next cancelation token
        # the push will be called in order or the page scroll, so no problem here.
        if self.has_cancel:
            if self.target == 'recent':
                if len(self.next_cancelation_tokens) < self.cancelation_tokens_count:
                    self.next_cancelation_tokens.add(id)

    def should_cancel(self):
        if self.has_cancel:
            # check if scraped_ids contains all cancelation_tokens (set inclusion)
            da = self.cancelation_tokens.issubset(self.scraped_ids)
            return da
        else:
            return False

    def parse(self, response):
        self.driver.get(response.url)

        try:
            entries = 0

            while not self.should_cancel():
                try:
                    # throttle the requests
                    entries += 1
                    sleep = random.uniform(3, 8) if self.randomize else 3
                    logging.info(
                        f"Entry: {entries}, sleeping for {math.floor(sleep)}")
                    time.sleep(sleep)

                    # Scroll down to the bottom
                    self.driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);")
                    # Scroll up a little bit
                    self.driver.execute_script("window.scrollBy(0, -300);")
                    time.sleep(0.5)
                    # Scroll back to the bottom
                    self.driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);")

                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located(
                            # this needs to be more dynamic
                            (By.CSS_SELECTOR, "div.feed_page--feedGrid--QViml"))
                    )
                except:
                    print("Error while scrolling down")
                    # Break the loop if there are no more items to load
                    break

                # Get the source code and parse it with Scrapy
                source = self.driver.page_source
                scrapy_selector = Selector(text=source)

                # Extract items
                # //div[contains(@class, "feed_page--feedGrid--QViml")]/div
                # => //div[contains(@class, "feedGrid")]/div
                items = scrapy_selector.xpath(
                    '//div[contains(@class, "feedGrid")]/div')

                for item in items:
                    # .//a[contains(@class, "feed_page--resourcePreview--RvDvR")]
                    # => .//a[contains(@class, "resourcePreview")]
                    link = item.xpath(
                        './/a[contains(@class, "resourcePreview")]/@href').get()
                    id = link.split('/')[-1]

                    # Skip already scraped items
                    if id in self.scraped_ids:
                        continue
                    else:
                        # .//a[contains(@class, "feed_page--title--VobyW")]
                        # => .//a[contains(@class, "feed_page--title")]
                        title = item.xpath(
                            './/a[contains(@class, "feed_page--title")]/text()').get()
                        thumbnail = item.xpath('.//img/@src').get()
                        # .//a[contains(@class, "feed_page--resourceMetaAuthor--JOdu5")]
                        # => .//a[contains(@class, "feed_page--resourceMetaAuthor")]
                        author_link = item.xpath(
                            './/a[contains(@class, "feed_page--resourceMetaAuthor")]/@href').get()

                        # .//span[contains(@class, "feed_page--author--yzyAW")]
                        # => .//span[contains(@class, "feed_page--author")]
                        author_name = item.xpath(
                            './/span[contains(@class, "feed_page--author")]/text()').get()
                        # .//div[contains(@class, "feed_page--action__default_like--wLEVs")]
                        # => .//div[contains(@class, "actions")]/div[contains(@class, "like")]
                        like_count = item.xpath(
                            './/div[contains(@class, "actions")]/div[contains(@class, "like")]/text()').get()

                        # .//div[contains(@class, "feed_page--newWindow--yr-g2")]
                        # => .//div[contains(@class, "actions")]/button/text()
                        duplicate_count = item.xpath(
                            './/div[contains(@class, "actions")]/button/text()').get()

                        like_count = tonum(like_count)
                        duplicate_count = tonum(duplicate_count)

                        # Save the data as JSON
                        data = {
                            "id": id,
                            "link": f"https://www.figma.com{link}",
                            "title": title,
                            "thumbnail": thumbnail,
                            "author_link": f"https://www.figma.com{author_link}",
                            "author_name": author_name,
                            "like_count": like_count,
                            "duplicate_count": duplicate_count,
                            # drop the milliseconds
                            "crawled_at": datetime.utcnow().replace(microsecond=0).isoformat()
                        }

                        self.push(id, data)
                        yield data

                print(f'{len(self.scraped_ids)} / {entries}', end='\r')
        except Exception as e:
            logging.error(f"Error occurred during scraping: {e}")

    def close(self, spider, reason):
        print("Closing spider")
        self.crawler.stats.set_value(
            'ci/next-cancelation-tokens', self.next_cancelation_tokens)
        self.driver.quit()


def tonum(txt: str):
    """
    converts human friendly numbers to integers
    """
    try:
        return int(float(txt.lower().replace(",", "").replace(
            ".", "").replace("k", "000").replace("m", "000000")))
    except ValueError:
        return 0
