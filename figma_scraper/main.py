import os
from scrapy import signals
from scrapy.signalmanager import dispatcher
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from figma_scraper.spiders.figma_spider import FigmaSpider  # import your spider here

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data')  # path to data directory

cancelation_tokens_file = os.path.join(
    DATA_DIR, '.spider/index/crawler.lock')


def get_cancelation_tokens():
    with open(cancelation_tokens_file, "r", encoding="utf-8") as f:
        # remove empty lines
        ids = [line.strip() for line in f if line.strip()]
        cancelation_tokens = set(ids)
        return cancelation_tokens


def set_cancelation_tokens(tokens):
    with open(cancelation_tokens_file, "w", encoding="utf-8") as f:
        f.write("\n".join(tokens))
        return True


def main():
    cancelation_tokens = get_cancelation_tokens()
    cancelation_tokens_count = len(cancelation_tokens)

    sort = 'recent'
    feed = 'output.recent.jsonl'

    def spider_closed(spider):
        # put your logic here
        stats = spider.crawler.stats.get_stats()
        next_cancelation_tokens = stats['ci/next-cancelation-tokens']
        print("Spider closed: %s" % spider.name)

        if next_cancelation_tokens and len(next_cancelation_tokens) >= cancelation_tokens_count:
            set_cancelation_tokens(next_cancelation_tokens)
        else:
            print(
                f"New cancelation tokens ({len(next_cancelation_tokens)}) were provided, but they are not enough to replace the old ones ({len(cancelation_tokens)}).")

    process = CrawlerProcess({
        **get_project_settings(),
        "LOG_ENABLED": True,
        "LOG_FILE": "scrapy.log",
        "LOG_LEVEL": "WARNING",
        "FEEDS": {
            feed: {"format": "jsonl"},
        },
    })

    dispatcher.connect(spider_closed, signal=signals.spider_closed)

    # Start your spider
    process.crawl(FigmaSpider, target=sort,
                  cancelation_tokens=cancelation_tokens)

    process.start()  # the script will block here until the crawling is finished

    # after closed.
    # read the feed file, compare with the main index file, add new items to the main index file


if __name__ == "__main__":
    main()

    # try:
    #     with open(self.output, "r", encoding="utf-8") as f:
    #         for line in f:
    #             data = json.loads(line)
    #             scraped_data.append(data)
    # except FileNotFoundError:
    #     pass
