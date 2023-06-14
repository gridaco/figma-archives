import click
from datetime import datetime
import json
import os
from scrapy import signals
from scrapy.signalmanager import dispatcher
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from figma_scraper.spiders.figma_spider import FigmaSpider  # import your spider here


@click.group()
def cli():
    pass


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'data')  # path to data directory

cancelation_tokens_file = os.path.join(
    DATA_DIR, '.spider/index/crawler.lock')

index_file = os.path.join(DATA_DIR, 'latest/index.json')


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


@cli.command('index')
@click.option('--timeout-minutes', default=0, help='Timeout in minutes (0 for no timeout)')
def ci_index(timeout_minutes):
    cancelation_tokens = get_cancelation_tokens()
    cancelation_tokens_count = len(cancelation_tokens)

    sort = 'recent'

    now = datetime.now()
    iso_now = now.replace(microsecond=0).isoformat()
    feed = f'out/output.recent@{iso_now}.jsonl'
    log = f'out/spider-index-{iso_now}.log'

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
        "LOG_FILE": log,
        "LOG_LEVEL": "WARNING",
        "CLOSESPIDER_TIMEOUT": timeout_minutes * 60,
        "FEEDS": {
            feed: {
                "format": "jsonlines",
                "encoding": "utf8",
            },
        },
    })

    dispatcher.connect(spider_closed, signal=signals.spider_closed)

    # Start your spider
    process.crawl(FigmaSpider, target=sort,
                  cancelation_tokens=cancelation_tokens)

    process.start()  # the script will block here until the crawling is finished

    # after closed.
    # read the feed file, compare with the main index file, add new items to the main index file
    with open(feed, "r", encoding="utf-8") as f:
        data_scraped = [json.loads(line) for line in f]
        ids_scraped = set([item['id'] for item in data_scraped])

    with open(index_file, "a+", encoding="utf-8") as f:
        f.seek(0)  # move the file pointer to the beginning of the file
        data_existing = [json.loads(line) for line in f]
        ids_existing = set([item['id'] for item in data_existing])

        # filter out existing ids from scraped ids
        ids_new = ids_scraped - ids_existing

        # filter out scraped data with existing ids
        data_new = [item for item in data_scraped if item['id'] in ids_new]

        # move the file pointer back to the end of the file
        f.seek(0, os.SEEK_END)

        # append new data to the main index file
        f.write("\n".join([json.dumps(item) for item in data_new]))
        # write trailing newline
        f.write("\n")


@cli.command("meta")
def ci_meta():
    ...


if __name__ == "__main__":
    cli()
