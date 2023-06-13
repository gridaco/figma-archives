import math
import random
import threading
import json
import time
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
from tqdm import tqdm


param_map = {
    'recent': 'new',  # https://www.figma.com/community/files/figma/free/new
    'trending': '',  # https://www.figma.com/community/files/figma/free/
    'popular': 'popular'  # https://www.figma.com/community/files/figma/free/popular
}


class FigmaSpider(scrapy.Spider):
    name = 'figma_spider'
    start_urls = []
    progress_bar = tqdm(total=1, desc="Crawling items", position=0)
    autosave_timer: threading.Timer = None

    def __init__(self, target='popular', **kwargs):
        # recent, trending, popular , e.g. pass with -a target=recent
        self.target = param_map[target]
        self.output = f'output.{target}.json'
        self.start_urls = [
            f'https://www.figma.com/community/files/figma/free/{self.target}']
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(service=Service(
            executable_path=ChromeDriverManager().install()), options=options)

    def parse(self, response):
        self.driver.get(response.url)
        scraped_data = []
        try:
            with open(self.output, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    scraped_data.append(data)
        except FileNotFoundError:
            pass

        scraped_ids = set(item['id'] for item in scraped_data)

        def save_data():
            with open(self.output, "w", encoding="utf-8") as f:
                for item in scraped_data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            tqdm.write(f"{len(scraped_data)} items saved to {self.output}")

        def save_data_periodically():
            save_data()
            self.autosave_timer = threading.Timer(
                600, save_data_periodically).start()

        save_data_periodically()

        entries = 0

        try:

            while True:
                try:
                    # throttle the requests
                    entries += 1
                    sleep = random.uniform(3, 8)
                    tqdm.write(
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
                            (By.CSS_SELECTOR, "div.feed_page--feedGrid--QViml"))
                    )
                except:
                    # Break the loop if there are no more items to load
                    break

                # Get the source code and parse it with Scrapy
                source = self.driver.page_source
                scrapy_selector = Selector(text=source)

                # Extract items
                items = scrapy_selector.xpath(
                    '//div[contains(@class, "feed_page--feedGrid--QViml")]/div')

                # update the progress bar
                _size = len(items)
                self.progress_bar.total = _size
                self.progress_bar.update(_size)

                for item in items:
                    link = item.xpath(
                        './/a[contains(@class, "feed_page--resourcePreview--RvDvR")]/@href').get()
                    id = link.split('/')[-1]

                    # Skip already scraped items
                    if id in scraped_ids:
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
                            # TODO: rename to like_count
                            "likes_count": like_count,
                            "duplicate_count": duplicate_count,
                            # drop the milliseconds
                            "crawled_at": datetime.utcnow().replace(microsecond=0).isoformat()
                        }

                        scraped_data.append(data)
                        scraped_ids.add(id)

            # Save the updated data to output.json
            with open(self.output, "w", encoding="utf-8") as f:
                for item in scraped_data:
                    f.write(json.dumps(item) + "\n")

        except Exception as e:
            tqdm.write(f"Error occurred during scraping: {e}")

        finally:
            tqdm.write("Script terminated")

            # save the data one last time
            save_data()

    def close_spider(self, spider):
        tqdm.write("Closing spider")
        self.autosave_timer.cancel()
        self.driver.quit()
        tqdm.write("Spider")


def tonum(txt: str):
    """
    converts human friendly numbers to integers
    """
    try:
        return int(float(txt.lower().replace(",", "").replace(
            ".", "").replace("k", "000").replace("m", "000000")))
    except ValueError:
        return 0
