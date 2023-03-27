import json
import scrapy
from scrapy.selector import Selector
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

class FigmaSpider(scrapy.Spider):
    name = 'figma_spider'
    start_urls = ['https://www.figma.com/community/files/figma/']

    def __init__(self):
        self.driver = webdriver.Chrome(service=Service(executable_path=ChromeDriverManager().install()))

    def parse(self, response):
        self.driver.get(response.url)
        scraped_data = []
        try:
            with open("output.json", "r") as f:
                for line in f:
                    data = json.loads(line)
                    scraped_data.append(data)
        except FileNotFoundError:
            pass

        scraped_ids = set(item['id'] for item in scraped_data)

        while True:
            try:
                # Scroll down to load more items
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.feed_page--feedGrid--QViml"))
                )
            except:
                # Break the loop if there are no more items to load
                break

            # Get the source code and parse it with Scrapy
            source = self.driver.page_source
            scrapy_selector = Selector(text=source)

            # Extract items
            items = scrapy_selector.xpath('//div[contains(@class, "feed_page--feedGrid--QViml")]/div')
            for item in items:
                link = item.xpath('.//a[contains(@class, "feed_page--resourcePreview--RvDvR")]/@href').get()
                id = link.split('/')[-1]

                # Skip already scraped items
                if id in scraped_ids:
                    continue
                else:
                    title = item.xpath('.//a[contains(@class, "feed_page--title--VobyW")]/text()').get()
                    thumbnail = item.xpath('.//img/@src').get()
                    author_link = item.xpath('.//a[contains(@class, "feed_page--resourceMetaAuthor--JOdu5")]/@href').get()
                    author_name = item.xpath('.//span[contains(@class, "feed_page--author--yzyAW")]/text()').get()
                    likes_count = item.xpath('.//div[contains(@class, "feed_page--action__default_like--wLEVs")]/text()').get()

                    # Save the data as JSON
                    data = {
                        "id": id,
                        "link": f"https://www.figma.com{link}",
                        "title": title,
                        "thumbnail": thumbnail,
                        "author_link": f"https://www.figma.com{author_link}",
                        "author_name": author_name,
                        "likes_count": int(likes_count) if likes_count else 0,
                        "crawled_at": datetime.utcnow().isoformat()
                    }

                    scraped_data.append(data)
                    scraped_ids.add(id)

        # Save the updated data to output.json
        with open("output.json", "w") as f:
            for item in scraped_data:
                f.write(json.dumps(item) + "\n")

    def close_spider(self, spider):
        self.driver.quit()
